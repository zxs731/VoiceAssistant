import os
from dotenv import load_dotenv  
import io 
import azure.cognitiveservices.speech as speechsdk
#from openai import AzureOpenAI
import openai
import time
import datetime  
import threading  
import json, ast
import pygame  
import requests, json
from io import BytesIO 
import tempfile 

from xiaoxin2_skill import *
from xiaoxin2_wakefromnetwork import *

load_dotenv("xiaoxin.env")  

os.environ["OPENAI_API_TYPE"] = os.environ["Azure_OPENAI_API_TYPE1"]
os.environ["OPENAI_API_BASE"] = os.environ["Azure_OPENAI_API_BASE1"]
os.environ["OPENAI_API_KEY"] = os.environ["Azure_OPENAI_API_KEY1"]
os.environ["OPENAI_API_VERSION"] = os.environ["Azure_OPENAI_API_VERSION1"]
BASE_URL=os.environ["OPENAI_API_BASE"]
API_KEY=os.environ["OPENAI_API_KEY"]
Chat_Deployment=os.environ["Azure_OPENAI_Chat_API_Deployment"]
Whisper_key=os.environ["Azure_Whisper_API_KEY"]
Whisper_endpoint = os.environ["Azure_Whisper_API_Url"]
Azure_speech_key= os.environ["Azure_speech_key"]
Azure_speech_region= os.environ["Azure_speech_region"]
Azure_speech_speaker= os.environ["Azure_speech_speaker"]
WakeupWord = os.environ["WakeupWord"]
WakeupModelFile=os.environ["WakeupModelFile"]
os.environ["AZURE_API_KEY"] =API_KEY
os.environ["AZURE_API_BASE"] =BASE_URL
os.environ["AZURE_API_VERSION"] =os.environ["Azure_OPENAI_API_VERSION1"]

   
messages = []
openai.api_key =API_KEY
openai.api_base = BASE_URL
openai.api_type = os.environ["OPENAI_API_TYPE"] 
openai.api_version = os.environ["OPENAI_API_VERSION"]


# Set up Azure Speech-to-Text and Text-to-Speech credentials
speech_key = Azure_speech_key
service_region = Azure_speech_region
speech_config = speechsdk.SpeechConfig(subscription=speech_key, region=service_region)
# Set up Azure Text-to-Speech language 
speech_config.speech_synthesis_language = "zh-CN"
# Set up Azure Speech-to-Text language recognition
speech_config.speech_recognition_language = "zh-CN"
#auto_detect_source_language_config = speechsdk.languageconfig.AutoDetectSourceLanguageConfig(languages=["en-US", "ja-JP","zh-CN"])
lang="zh-CN"
# Set up the voice configuration
speech_config.speech_synthesis_voice_name = Azure_speech_speaker
speech_synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config)

# Creates an instance of a keyword recognition model. Update this to
# point to the location of your keyword recognition model.
model = speechsdk.KeywordRecognitionModel(WakeupModelFile)
# The phrase your keyword recognition model triggers on.
keyword = WakeupWord
# Create a local keyword recognizer with the default microphone device for input.
#keyword_recognizer = speechsdk.KeywordRecognizer()
done = False

# Set up the audio configuration
audio_config = speechsdk.audio.AudioConfig(use_default_microphone=True)
# Create a speech recognizer and start the recognition
speech_recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config,  audio_config=audio_config)
unknownCount=0
sysmesg={"role": "system", "content": os.environ["sysprompt_"+lang]}

# Define the speech-to-text function
def speech_to_text():
    global unknownCount
    global lang
    print("Please say...")

    result = speech_recognizer.recognize_once_async().get()
    '''
    auto_detect_source_language_result = speechsdk.AutoDetectSourceLanguageResult(result)
    detected_language = auto_detect_source_language_result.language
    print(detected_language)
    
    if detected_language and detected_language !="Unknown":
        lang=detected_language
    '''    
    if result.reason == speechsdk.ResultReason.RecognizedSpeech:
        unknownCount=0
        return result.text
    elif result.reason == speechsdk.ResultReason.NoMatch:
        unknownCount+=1
        error= os.environ["sorry_"+lang]
        text_to_speech(error)
        return error
    elif result.reason == speechsdk.ResultReason.Canceled:
        return "speech recognizer canceled."

# Define the text-to-speech function
def text_to_speech(text):
    try:
        # 使用SSML来调整合成速度  
        ssml_text = f''' 
           <speak xmlns="http://www.w3.org/2001/10/synthesis" xmlns:mstts="http://www.w3.org/2001/mstts" xmlns:emo="http://www.w3.org/2009/10/emotionml" version="1.0" xml:lang="{lang}"><voice name="{speech_config.speech_synthesis_voice_name}"><prosody rate="+20.00%">{text}</prosody></voice></speak>
        '''  
          
        # 合成文本  
        result = speech_synthesizer.speak_ssml_async(ssml_text).get()  
        #result = speech_synthesizer.speak_text_async(text).get()
        if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
            print("Text-to-speech conversion successful.")
            return True
        else:
            print(f"Error synthesizing audio: {result}")
            return False
    except Exception as ex:
        print(f"Error synthesizing audio: {ex}")
        return False

# Define the Azure OpenAI language generation function
def generate_text(prompt):
    global messages
    #global quitReg
    #global pause
    
    messages.append({"role": "user", "content": prompt})
    tools=getTools()
    cont = run_conversation(messages,tools)
    return cont["content"]
    

def getLLMResponse(messages,tools):
    i=20
    messages_ai = messages[-i:]
    while 'role' in messages_ai[0] and messages_ai[0]["role"] == 'tool':
        i+=1
        messages_ai = messages[-i:]
    sysmesg={"role": "system", "content": getSystemPrompt()}    #os.environ["sysprompt_"+lang]
    response = openai.ChatCompletion.create(
        engine=Get_Chat_Deployment(),
        messages=[sysmesg]+messages_ai,
        temperature=0.6,
        max_tokens=500,
        tools=tools,
        tool_choice="auto",  # auto is default, but we'll be explicit
        stream=False
    )
    return response.choices[0].message



def run_conversation(messages,tools):
    # Step 1: send the conversation and available functions to the model
    response_message = getLLMResponse(messages,tools)
    
    # Step 2: check if the model wanted to call a function
    if 'tool_calls' in response_message:
        tool_calls = response_message.tool_calls
        # Step 3: call the function
        messages.append(response_message)  # extend conversation with assistant's reply
        # Step 4: send the info for each function call and function response to the model
        for tool_call in tool_calls:
            print(f'⏳Call internal function...')
            function_name = tool_call.function.name
            print(f'⏳Call {function_name}...')
            function_to_call = globals()[function_name]
            function_args = json.loads(tool_call.function.arguments)
            
            print(f'⏳Call params: {function_args}')
            function_response = function_to_call(**function_args)
            print(f'⏳Call internal function done! ')
            print("执行结果：")
            print(function_response)
            print("===================================")
            messages.append(
                {
                    "tool_call_id": tool_call.id,
                    "role": "tool",
                    "name": function_name,
                    "content": function_response,
                }
            )  # extend conversation with function response
            
        response_message = run_conversation(messages,tools)
        return response_message
    else:
        print(f'Final result: {response_message["content"]}')
        return response_message

def recognized_cb(evt):
    # Only a keyword phrase is recognized. The result cannot be 'NoMatch'
    # and there is no timeout. The recognizer runs until a keyword phrase
    # is detected or recognition is canceled (by stop_recognition_async()
    # or due to the end of an input file or stream).
    result = evt.result
    if result.reason == speechsdk.ResultReason.RecognizedKeyword:
        print("RECOGNIZED KEYWORD: {}".format(result.text))
    global done
    done = True

def canceled_cb(evt):
    result = evt.result
    if result.reason == speechsdk.ResultReason.Canceled:
        print('CANCELED: {}'.format(result.cancellation_details.reason))
    global done
    done = True

stop_do_reminder_loop=False
def do_reminder_loop():  
    print("start a thread to loop check reminder......")
    while True:  
        # 检查是否需要停止线程  
        if stop_do_reminder_loop:  
            print("Reminder thread is stopping")  
            break  
  
        # 这里是线程的工作代码  
        #print("Thread is running...")
        checkReminders(text_to_speech)
        time.sleep(3)  
# 获取当前时间  
start_time = datetime.datetime.now()  
end_time = start_time
  
pre_questionFromNet=None

while True and (not isrestart()):
    # 创建一个新的线程来运行checkReminders函数  
    stop_do_reminder_loop=False
    t=None
    if getCheckMessage():
        t = threading.Thread(target=do_reminder_loop, args=()) 
        # 开始运行新的线程  
        t.start()  
    questionFromNet = getQuestionFromNet() if getCheckMessage() else "None"
    if pre_questionFromNet==questionFromNet:
        questionFromNet = "None" 
    else:
        pre_questionFromNet=questionFromNet 
        
    if questionFromNet == "None" :
        keyword_recognizer=speechsdk.KeywordRecognizer()
        # Connect callbacks to the events fired by the keyword recognizer.
        keyword_recognizer.recognized.connect(recognized_cb)
        keyword_recognizer.canceled.connect(canceled_cb)
        text_to_speech(os.environ["welcome_"+lang])
        # Start keyword recognition.
        result_future = keyword_recognizer.recognize_once_async(model)

        while True:        
            print('Say something starting with "{}" followed by whatever you want...'.format(keyword))            
            result = result_future.get()
            # Read result audio (incl. the keyword).
            if result.reason == speechsdk.ResultReason.RecognizedKeyword:
                print("Keyword recognized")
                if isPlaying():
                    pauseplay()

                break
            else:
                print("Keyword not recognized")

        
    #stop reminder loop
    stop_do_reminder_loop=True
    if t!=None:
        t.join()
    if questionFromNet == "None":
        text_to_speech(os.environ["hello_"+lang])
    else:
        text_to_speech("你好！我收到了一个留言信息，内容如下：")
        t2 = threading.Thread(target=text_to_speech, args=(questionFromNet,)) 
        # 开始运行新的线程  
        t2.start()  
    
    
    # 计算时间间隔  
    time_interval = end_time - start_time  
    # Main program loop
    print(f'isPlaying():{isPlaying()}')
    print(f'isPause():{isPause()}')
    
    while unknownCount<2 and time_interval.total_seconds() < 30 and (not isPlaying()) and (not quit()):
        end_time = datetime.datetime.now()  
        # Get input from user using speech-to-text
        user_input = speech_to_text() if (questionFromNet == "None") else questionFromNet
        questionFromNet="None"
        start_time = datetime.datetime.now()  
        print(f"You said: {user_input}")
    
        # Generate a response using OpenAI
        #prompt = f"Q: {user_input}\nA:"
        response = generate_text(user_input)
        #response = user_input
        print(f"AI says: {response}")
    
        # Convert the response to speech using text-to-speech
        text_to_speech(response)
        #assistant_speaking_thread = threading.Thread(target=text_to_speech, args=(response,)) 
        #assistant_speaking_thread.start()  
        messages.append({"role": "assistant", "content": response})
        start_time = datetime.datetime.now()  
        checkReminders(text_to_speech)  
        time.sleep(3)  
    
    if isPause():
        unpauseplay()
        
    time.sleep(1)  
    if(not isPlaying() and not isrestart()):
        text_to_speech(os.environ["bye_"+lang])
    unknownCount=0
    
if isrestart():
    start()
    