import azure.cognitiveservices.speech as speechsdk
import time
import json
from num2words import num2words
import math
import shutil

import subprocess
import os

trim_up_timestamps = []
hitword = 'take'
export_timestamps = []
items = []
time_buffer = 1.0
input_file = 'troll'
output_file = 'final'
temp_path = 'temp'

try:
    os.mkdir(temp_path)
except OSError:
    print("Creation of the directory %s failed" % temp_path)
else:
    print("Successfully created the directory %s " % temp_path)

command = f"ffmpeg -i {input_file}.mp4 -ab 160k -ac 2 -ar 48000 -vn {temp_path}/extracted.wav"
subprocess.call(command, shell=True)


# Creates an instance of a speech config with specified subscription key and service region.
speech_key, service_region = "8bb7285d48e640098d0e3e3e2dd3021b", "eastus"
speech_config = speechsdk.SpeechConfig(
    subscription=speech_key, region=service_region)
speech_config.request_word_level_timestamps()
audio_filename = f"{temp_path}/extracted.wav"
# audio_filename = "test_footage/Google-test.wav"
audio_input = speechsdk.AudioConfig(filename=audio_filename)
speech_recognizer = speechsdk.SpeechRecognizer(
    speech_config=speech_config, audio_config=audio_input)


def start():
    done = False

    def stop_callback(evt):
        print("Closing on {}".format(evt))
        speech_recognizer.stop_continuous_recognition()

        for item in trim_up_timestamps:
            current_transcript = item['transcript']

            for i in range(10):
                if str(i+1) in current_transcript:
                    items.append(i+1)

        print(items, trim_up_timestamps, '\n')

        nonlocal done
        done = True

    def add_to_res(evt):
        py_dict = json.loads(evt.result.json)
        transcript = py_dict['DisplayText']
        if hitword in transcript.lower():
            for i in range(10):
                target_num_word = num2words(i+1, lang='en')
                if target_num_word in transcript.lower():
                    transcript = transcript.replace(target_num_word, str(i+1))

            start_time = int(py_dict['Offset'])/10000000
            end_time = (int(py_dict['Offset']) +
                        int(py_dict['Duration']))/10000000
            my_dict = {'transcript': transcript,
                       'start': start_time, 'end': end_time}

            trim_up_timestamps.append(my_dict)

    # Connect callbacks to the events fired by the speech recognizer
    # speech_recognizer.recognizing.connect(lambda evt: print('RECOGNIZING: {}'.format(evt)))
    # speech_recognizer.recognized.connect(lambda evt: print('RECOGNIZED: {}'.format(evt)))
    # speech_recognizer.recognized.connect(add_to_res)
    speech_recognizer.recognized.connect(add_to_res)

    # speech_recognizer.session_started.connect(lambda evt: print('SESSION STARTED: {}'.format(evt)))
    # speech_recognizer.session_stopped.connect( lambda evt: print('SESSION STOPPED {}'.format(evt)))
    # speech_recognizer.canceled.connect( lambda evt: print('CANCELED {}'.format(evt)))
    # stop continuous recognition on either session stopped or canceled events
    speech_recognizer.session_stopped.connect(stop_callback)

    # Start continuous speech recognition
    speech_recognizer.start_continuous_recognition()
    while not done:
        time.sleep(.5)
    # </SpeechContinuousRecognitionWithFile>


start()

del speech_recognizer

min_index = 0
outside_temp_array = []
for i in range(len(items)):
    temp_item = items[min_index]
    temp_array = items[min_index+1:]

    for j in range(len(temp_array)):
        if temp_item == temp_array[j]:
            print(temp_item, temp_array[j],
                  i, j, min_index, temp_array)
            outside_temp_array.append(temp_item)
            print('Start', trim_up_timestamps[min_index]['end'],
                  'End', trim_up_timestamps[min_index+1 + j]['start'])

            frac1, whole1 = math.modf(
                trim_up_timestamps[min_index]['end'] + time_buffer)
            temp_duration = (trim_up_timestamps[min_index+1 + j]['start'] - time_buffer) - (
                trim_up_timestamps[min_index]['end'] + time_buffer)
            frac2, whole2 = math.modf(
                temp_duration)

            my_dict = {'start': time.strftime('%H:%M:%S', time.gmtime(whole1)) + '.' + str(round(frac1, 2))[
                2:], 'duration': time.strftime('%H:%M:%S', time.gmtime(whole2)) + '.' + str(round(frac2, 2))[2:]}
            #my_dict = {'start': time.strftime('%H:%M:%S', time.gmtime(whole1)), 'end': time.strftime('%H:%M:%S', time.gmtime(whole2))}
            export_timestamps.append(my_dict)

            min_index = min_index + 1 + j + 1
            break

    if min_index == len(items):
        break

print(outside_temp_array)
print(export_timestamps)
final_exports = []

for i in range(len(export_timestamps)):
    if i > 0 and outside_temp_array[i] > outside_temp_array[i-1]:
        del export_timestamps[i-1]

print(export_timestamps)

file = open(f"{temp_path}/files.txt", "a+")
for i in range(len(export_timestamps)):
    command = f"ffmpeg -ss {export_timestamps[i]['start']} -i {input_file}.mp4 -t {export_timestamps[i]['duration']} -c copy -avoid_negative_ts 1 {temp_path}/output{i}.mp4"
    subprocess.call(command, shell=True)

    file.write(f"file output{i}.mp4")
    file.write("\n")

file.close()

command = f"ffmpeg -f concat -i {temp_path}/files.txt -c copy -avoid_negative_ts 1 {output_file}.mp4\n"
subprocess.call(command, shell=True)

try:
    shutil.rmtree(f"{temp_path}", ignore_errors=False)
except OSError as e:
    print("Error: %s : %s" % (f"{temp_path}", e.strerror))
