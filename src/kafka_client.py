

# STANDARD MODULES
import os
import sys
import time
import json
import requests
import traceback
from kafka import KafkaClient
from kafka import KafkaConsumer
from src.commonlib.commonlib.kafka_producer import KafkaProducer

# from kafka_handler import CommonKafkaProducer
from string import Template

# USERDEFINED FILES
# from config import KAFKA, EXPONENT
# from config import EMAIL_ENDPOINT, EMAIL_CONTENT


def isReachable(server):
    """
        Returns True is server is reachable, False otherwise
    """
    command = "ping -c 1 {}".format(KAFKA['SERVER'])
    response = os.system(command)
    if response == 0:
        return True
    return False


def get_localtime():
    """
        Returns current date and time
    """
    localtime = time.strftime("%A %B %d %Y %I:%M:%S %p %Z", time.localtime())
    return localtime


def get_timestamp():
    """
        Return the current timestamp
    """
    return int(time.time())


def update_timestamp(record, retry):
    """
        Update the retry count and timestamp in record
    """
    record['retry'] = retry
    record['timestamp'] = get_timestamp()
    return record


def capture_traceback():
    """
        Capture error tracebacks on exceptional scenarios
        Call this method in all except blocks
    """
    exc_type, exc_value, exc_traceback = sys.exc_info()
    formatted_lines = traceback.format_exc().splitlines()
    print(">" * 79)
    for line in formatted_lines:
        print(line)
    print(">" * 79)


def exponential_lookup(server, port, topic, record):
    """
        Perform an exponential lookup for endpoint accessibility for processing the data
    """
    try:
        # Instantiate a Producer object
        producer = Producer(server, port)

        updated_by = record["updated_by"]
        data = record["data"]
        if record["type"] == "API" or "type" not in record:
            # Endpoint info
            endpoint = record["endpoint"]
            # Push data to endpoint
            try:
                headers = {'Content-type': 'application/json'}
                r = requests.post(endpoint, data=json.dumps(data), headers=headers)
                if r.status_code == 200:
                    status = 202
                    output = "Data accepted for processing"
                    response = {"status": status, "output": output}
                    print("Endpoint: [{}] is accessible and data pushed for processing".format(endpoint))
                    print(response)
                    return
            except:
                pass
        elif record["type"] == "kafka":
            # Push data to Kafka
            try:
                kafka = CommonKafkaProducer(record['host'])
                kafka.put(record['topic'], data)
                status = 200
                output = "Data processed"
                response = {"status": status, "output": output}
                print("Kafka Server: [{}] is accessible and data pushed for processing".format(record['host']))
                print(response)
                return
            except:
                pass

        # Check if record holds a retry key:
        if "retry" not in record:
            # Update retry count and current timestamp in record
            retry = 1
            record = update_timestamp(record, retry)

            # Push message back to kafka queue
            producer.put(topic, record)
        else:
            # Compare elapsed seconds for record
            retry = record['retry']
            prev_timestamp = record['timestamp']
            curr_timestamp = get_timestamp()
            elapsed_seconds = curr_timestamp - prev_timestamp

            # Exit from exponential search
            if retry == len(EXPONENT):
                # Notify endpoint owner when retry exceeds its limit...
                try:
                    email_endpoint, email_content = EMAIL_ENDPOINT, EMAIL_CONTENT
                    username = updated_by.capitalize()
                    to = username + '@vmware.com'
                    email_content["to"] = [to]
                    email_content["data"]["username"] = username
                    email_content["data"]["endpoint"] = endpoint  # Original endpoint ref. of data
                    email_content["data"]["payload"] = str(json.dumps(data))
                    r = requests.post(email_endpoint, data=json.dumps(email_content), headers=headers)
                    if r.status_code == 200:
                        status = 202
                        output = "Notified endpoint owner: Retry exceeded its limit. Dropping msg from queue..."
                        response = {"status": status, "output": output}
                        print(response)
                except:
                    status = 500
                    output = "Error occurred while sending notification to endpoint owner"
                    response = {"status": status, "output": output}
                    print(response)
                    capture_traceback()
                return

            # Compare elapsed seconds with exponential configuration
            for index, tries in enumerate(EXPONENT):
                exponential_seconds = tries.get(index + 1)
                if exponential_seconds >= elapsed_seconds:
                    if retry < len(EXPONENT):
                        retry += 1
                        record = update_timestamp(record, retry)
                        # Push message back to kafka queue
                        producer.put(topic, record)
    except:
        print("\n>>> Error:")
        capture_traceback()


class Consumer(object):
    """
        Consumer class used to fetch message from kafka messaging queue
    """

    def __init__(self, server, port, topic):
        """
            Constructor: Initialise kafka server
        """
        self.server = server
        self.port = port
        self.topic = topic
        kafka_server = "{}:{}".format(self.server, self.port)
        self.consumer = KafkaConsumer(self.topic,
                                      bootstrap_servers=[kafka_server],
                                      auto_offset_reset="earliest",
                                      session_timeout_ms=290000,  # Session timeout should be less than request timeout.
                                      request_timeout_ms=300000,
                                      # Request timeout should sync with the actual execution time for successfull execution completion
                                      # and it should be match with the group.max.session.timeout.ms settings on server side.
                                      enable_auto_commit=True,
                                      group_id='1', )

        # Check whether you are able to connect to message queue
        if self.consumer is not None:
            print("Succesfully connected to the Message queue.")
        else:
            print("Failed to connect to the Message queue.")

    def get(self):
        """
            Get message from queue
        """
        # Reading messages from queue
        for message in self.consumer:
            record = json.loads(message.value.decode('utf-8'))
            # Get message from kafka messaging queue
            print("\nMessage from kafka queue: {} extracted successfully at {}".format(self.topic, get_localtime()))
            print("<<< {}\n".format(record))

            # Perform a exponential lookup for endpoint accessibility to process the data
            exponential_lookup(self.server, self.port, self.topic, record)

            # Execution proceeds futher to fetch next message from kafka queue
            # If queue is empty then it waits till the message arrives to kafka queue

    def __del__(self):
        """
            Destructor: Closing the producer object
        """
        self.consumer.close()


if __name__ == "__main__":
    # ------------------------------------------------------------------------
    # Kafka Consumer Execution Point
    # ------------------------------------------------------------------------
    # Read inputs
    server = KAFKA['SERVER']
    port = KAFKA['PORT']
    topic = KAFKA['TOPIC']

    # Check whether kafka server is reachable
    if isReachable(server):
        # Instantiate a kafka object
        kafka = Consumer(server, port, topic)

        # Daemon call: Fetch message from kafka queue
        kafka.get()
    else:
        print("Kafka Server: {}:{} is down. Quitting...".format(server, port))
        sys.exit(1)
