import os
from dotenv import load_dotenv  
import io 
import azure.cognitiveservices.speech as speechsdk
from zhipuai import ZhipuAI
import time
import datetime  
load_dotenv("xiaoxin_glm.env")  
client = ZhipuAI(api_key=os.environ["glm_key"]) 
modelName = os.environ["glm_model"]
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


# Set up Azure Speech-to-Text and Text-to-Speech credentials
speech_key = Azure_speech_key
service_region = Azure_speech_region
speech_config = speechsdk.SpeechConfig(subscription=speech_key, region=service_region)
# Set up Azure Text-to-Speech language 
speech_config.speech_synthesis_language = "zh-CN"
# Set up Azure Speech-to-Text language recognition
#speech_config.speech_recognition_language = "en-US"
auto_detect_source_language_config = speechsdk.languageconfig.AutoDetectSourceLanguageConfig(languages=["en-US", "ja-JP","zh-CN"])
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
speech_recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config,auto_detect_source_language_config=auto_detect_source_language_config,  audio_config=audio_config)
unknownCount=0
sysmesg={"role": "system", "content": os.environ["sysprompt_"+lang]}
messages=[]
# Define the speech-to-text function
def speech_to_text():
    global unknownCount
    global lang
    print("Please say...")

    result = speech_recognizer.recognize_once_async().get()
    auto_detect_source_language_result = speechsdk.AutoDetectSourceLanguageResult(result)
    detected_language = auto_detect_source_language_result.language
    print(detected_language)
    
    if detected_language and detected_language !="Unknown":
        lang=detected_language
        
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
    sysmesg={"role": "system", "content": os.environ["sysprompt_"+lang]}
    messages.append({"role": "user", "content": prompt})
    
    completion = client.chat.completions.create(
                model=modelName,
                messages=messages[-15:]
            )
    '''
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
    '''
    ##cont=completion["choices"][0]["message"]["content"]
    cont=completion.choices[0].message.content
    
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
    text_to_speech(os.environ["welcome_"+lang])
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
            
    text_to_speech(os.environ["hello_"+lang])
    
    # 计算时间间隔  
    time_interval = end_time - start_time  
    # Main program loop
    while unknownCount<2 and time_interval.total_seconds() < 30:
        end_time = datetime.datetime.now()  
        # Get input from user using speech-to-text
        user_input = speech_to_text()
        start_time = datetime.datetime.now()  
        print(f"You said: {user_input}")
    
        # Generate a response using OpenAI
        #prompt = f"Q: {user_input}\nA:"
        response = generate_text(user_input)
        #response = user_input
        print(f"AI says: {response}")
    
        # Convert the response to speech using text-to-speech
        text_to_speech(response)
        messages.append({"role": "assistant", "content": response})
        start_time = datetime.datetime.now()  
    
    time.sleep(1)  
    text_to_speech(os.environ["bye_"+lang])
    unknownCount=0
    