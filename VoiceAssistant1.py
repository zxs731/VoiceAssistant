import os
from dotenv import load_dotenv  
import io 
import azure.cognitiveservices.speech as speechsdk
#from openai import AzureOpenAI
import openai
import time
import datetime  
load_dotenv("en.env")  

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
speech_recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config, audio_config=audio_config)
unknownCount=0
sysmesg={"role": "system", "content": "你是一名人工智能助手，请帮助我们寻找需要的信息."}
messages=[]
# Define the speech-to-text function
def speech_to_text():
    global unknownCount
    print("请跟我聊点什么吧...")

    result = speech_recognizer.recognize_once_async().get()

    if result.reason == speechsdk.ResultReason.RecognizedSpeech:
        unknownCount=0
        return result.text
    elif result.reason == speechsdk.ResultReason.NoMatch:
        unknownCount+=1
        error="对不起，我没有听懂"
        text_to_speech(error)
        return error
    elif result.reason == speechsdk.ResultReason.Canceled:
        return "语音识别取消."

# Define the text-to-speech function
def text_to_speech(text):
    try:
        result = speech_synthesizer.speak_text_async(text).get()
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
    messages.append({"role": "user", "content": prompt})
    completion = openai.ChatCompletion.create(
          engine=Chat_Deployment,
          messages = [sysmesg]+messages[-10:],
          temperature=0.7,
          max_tokens=500,
          top_p=0.95,
          frequency_penalty=0,
          presence_penalty=0,
          stop=None
        )
    cont=completion["choices"][0]["message"]["content"]
    return cont
    #return response.choices[0].message.content

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

# 获取当前时间  
start_time = datetime.datetime.now()  
end_time = start_time
  

while True:
    keyword_recognizer=speechsdk.KeywordRecognizer()
    # Connect callbacks to the events fired by the keyword recognizer.
    keyword_recognizer.recognized.connect(recognized_cb)
    keyword_recognizer.canceled.connect(canceled_cb)
    # Start keyword recognition.
    result_future = keyword_recognizer.recognize_once_async(model)
    
    while True:        
        print('Say something starting with "{}" followed by whatever you want...'.format(keyword))
        
        result = result_future.get()
    
        # Read result audio (incl. the keyword).
        if result.reason == speechsdk.ResultReason.RecognizedKeyword:
           print("Keyword recognized")
           break
        else:
           print("Keyword not recognized")
            
    text_to_speech(f'你好，很高兴为您服务。我在听请讲。')
    # 计算时间间隔  
    time_interval = end_time - start_time  
    # Main program loop
    while unknownCount<3 and time_interval.total_seconds() < 30:
        end_time = datetime.datetime.now()  
        # Get input from user using speech-to-text
        user_input = speech_to_text()
        start_time = datetime.datetime.now()  
        print(f"You said: {user_input}")
    
        # Generate a response using OpenAI
        prompt = f"Q: {user_input}\nA:"
        response = generate_text(user_input)
        #response = user_input
        print(f"AI says: {response}")
    
        # Convert the response to speech using text-to-speech
        text_to_speech(response)
        messages.append({"role": "assistant", "content": response})
        start_time = datetime.datetime.now()  

    text_to_speech(f'我先退下了，您可以再次唤醒我，说：“{keyword}”，再会！')
    unknownCount=0
    time.sleep(0.1)  
