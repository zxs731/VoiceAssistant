import json, ast
import pygame  
import requests, json
from io import BytesIO 
import tempfile 
import time
import datetime  
import io 
import dateutil.parser  
import locale 
import os
from dotenv import load_dotenv  
import subprocess  

load_dotenv("xiaoxin.env")  
quitReg=False
pause=False
playing=False
def NewContent(content):
    # 获取当前日期和时间  
    now = datetime.datetime.now()  

    # 将日期转换为字符串格式，例如：“2023年4月10日”  
    date_string = now.strftime("%Y年%m月%d日")  
     
    print(date_string)  
    current_time = now.strftime("%H点%M分%S秒")  
    print(current_time) 
    
    try:
        # 打开文件以追加模式写入  
        file = open(f'{date_string}.md', "a") 
        # 追加内容  
        file.write(f'''
{content} 【记录时间：{current_time}】''')  
        # 关闭文件  
        file.close() 
        return f'日记已添加成功！'
    except Exception as e:  
        return f'日记添加失败！请稍后再试！'
    
fun_newcontent_desc = {
    "type": "function",
    'function':{
        'name': 'NewContent',
        'description': '添加内容到日记',
        'parameters': {
            'type': 'object',
            'properties': {
                'content': {
                    'type': 'string',
                    'description': '用户提供的日记内容,内容可以是markdown格式的任何文本。注意：只需要增量内容，不要重复内容。'
                },
            },
            'required': ['content']
        }
    }
}
def playmusic(song_name):
    global playing, pause 
    url='http://music.163.com/api/search/get/web?csrf_token=hlpretag=&hlposttag=&s= %s&type=1&offset=0&total=true&limit=10' % song_name
    res=requests.get(url)
    music_json=json.loads(res.text)
    count=music_json["result"]["songCount"]
    if(count>0):
        if downloadAndPlay(music_json,0):
            return "歌曲："+song_name+" 开始播放。请欣赏，我先退下了。"
        else:
            playing=False
            pause = False
            return "没有可以播放的歌曲！"
    
    return "没找到该歌曲！"

def downloadAndPlay(music_json,index):
    global playing, pause 
    count=music_json["result"]["songCount"]
    if index>=count:
        return False
    songid=music_json["result"]["songs"][index]["id"]
    url='http://music.163.com/song/media/outer/url?id=%s.mp3' % songid
    response = requests.get(url)  
    audio_data = BytesIO(response.content)  

    temp_file_name = "temp_audio.mp3"  # 临时文件名  
    with open(temp_file_name, 'wb') as temp_file:  
        temp_file.write(audio_data.getbuffer())  
    print(temp_file_name)

    # 初始化pygame  
    pygame.init()  
    try:
        # 播放音乐  
        pygame.mixer.music.load(temp_file_name)  
        pygame.mixer.music.play()
        playing=True
        pause = False
        return True
    except Exception as e:  
        print("failed play try next one")
        playing=False
        pause = False
        index+=1
        return downloadAndPlay(music_json,index)
        
    
fun_playmusic_desc = {
    "type": "function",
    'function':{
        'name': 'playmusic',
        'description': '播放歌曲',
        'parameters': {
            'type': 'object',
            'properties': {
                'song_name': {
                    'type': 'string',
                    'description': '歌名'
                },
            },
            'required': ['song_name']
        }
    }
}
def stopplay():
    global playing, pause 
    pygame.mixer.music.stop()  
    playing=False
    pause = False
    return "播放已停止。"
    
fun_stopplay_desc = {
    "type": "function",
    'function':{
        'name': 'stopplay',
        'description': '停止播放',
        'parameters': {
            'type': 'object',
            'properties': {

            },
            'required': []
        }
    }
}
def pauseplay():
    global playing, pause
    pygame.mixer.music.pause()

    playing=False
    pause = True
    return "播放已暂停。"

fun_pauseplay_desc = {
    "type": "function",
    'function':{
        'name': 'pauseplay',
        'description': '暂停播放',
        'parameters': {
            'type': 'object',
            'properties': {

            },
            'required': []
        }
    }
}

def unpauseplay():
    global playing, pause
    pygame.mixer.music.unpause()
    playing=True
    pause = False
    return "恢复播放"

fun_unpauseplay_desc = {
    "type": "function",
    'function':{
        'name': 'unpauseplay',
        'description': '恢复播放',
        'parameters': {
            'type': 'object',
            'properties': {

            },
            'required': []
        }
    }
}
def isPause():
    return pause

def isPlaying():
    return playing

reminders=[]
def currentDatetime():
    locale.setlocale(locale.LC_TIME, 'zh_CN.UTF-8')  
      
    now = datetime.datetime.now()  
    current_datetime = now.strftime("%Y年%m月%d日 %A %H时%M分%S秒")  
    print("currentDatetime: "+current_datetime)
    return current_datetime
    
fun_currentDatetime_desc = {
    "type": "function",
    'function':{
        'name': 'currentDatetime',
        'description': '获取现在的日期和时间',
        'parameters': {
            'type': 'object',
            'properties': {

            },
            'required': []
        }
    } 
}
def addReminder(target:str, content: str):  
    reminders.append({'target':target,"content":content})
    print(f"提醒:【{content}】已添加到{target}") 
    return f'定时提醒已添加'
    
tool_addReminder_des={
            "type": "function",
            "function": {
                "name": "addReminder",
                "description": "添加提醒",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "target": {
                            "type": "string",
                            "description": "提醒的具体时间，格式为：%Y-%m-%d %H:%M:%S",
                        },
                        "content": {
                            "type": "string",
                            "description": "提醒内容",
                        },
                        
                    },
                    "required": ["target","content"],
                },
            },
        }    
def removeReminder(content: str): 
    global reminders
    hasRemoved=False
    for reminder in reminders:
        if content in reminder["content"]:
            hasRemoved=True
            break
    reminders[:] = [reminder for reminder in reminders if content not in reminder.get('content')]  
    if hasRemoved:        
        print(f"提醒:【{content}】已从提醒列表移除") 
        return f'提醒已从列表移除'
    else:
        print(f"没有找到可移除的提醒！") 
        return f'没有找到可移除的提醒'
    
    
tool_removeReminder_des={
            "type": "function",
            "function": {
                "name": "removeReminder",
                "description": "移除提醒",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "content": {
                            "type": "string",
                            "description": "要移除的提醒",
                        },
                        
                    },
                    "required": ["content"],
                },
            },
        } 

 
def checkReminders(feedback):
    global reminders
    now = datetime.datetime.now()
    #print(reminders)
    #print(now)
    for reminder in reminders:  
        target = dateutil.parser.parse(reminder['target'])  
        if target <= now <= (target + datetime.timedelta(minutes=10)):  
            print(reminder['content'])
            feedback(f"请注意，{reminder['content']}的提醒到时间了。如取消提醒请告诉我。")
            
deploymentModel = None          
def setLLMVersion(deployment="GPT3.5"):
    global deploymentModel
    print("setLLMVersion: "+deployment)
    if deployment!="GPT3.5":
        deploymentModel= os.environ["Azure_OPENAI_Chat_API_Deployment_GPT4"]  
    else:
        deploymentModel = os.environ["Azure_OPENAI_Chat_API_Deployment"]
    return f"大模型已切换为：{deployment}"
        
    
tool_setLLMVersion_des={
            "type": "function",
            "function": {
                "name": "setLLMVersion",
                "description": "切换大模型的版本",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "deployment": {"type": "string", "enum": ["GPT3.5", "GPT4"]},
                    },
                    "required": ["deployment"],
                },
            },
        }
def Get_Chat_Deployment():
    global deploymentModel
    if not deploymentModel:
        deploymentModel = os.environ["Azure_OPENAI_Chat_API_Deployment"]    
    return deploymentModel

checkMessage=False
def CheckMessage(isOpen):
    global checkMessage
    checkMessage=(isOpen==1)
    return "网络唤醒已设置为开启" if isOpen==1 else "网络唤醒已设置为关闭"

tool_CheckMessage_des={
            "type": "function",
            "function": {
                "name": "CheckMessage",
                "description": "将网络唤醒功能设置为打开或关闭",
                "parameters": {
                    "type": "object",
                    "properties": {
                       "isOpen": {"type": "number","description": "网络唤醒（打开）为:1,网络唤醒（关闭）为:0",},
                    },
                    "required": ["isOpen"],
                },
            },
        }
def getCheckMessage():
    global checkMessage
    return checkMessage

isquit=False
def setQuit(isQuit):
    global isquit
    isquit=(isQuit==1)
    return "服务即将退出" if isquit else "继续为您服务"

tool_setQuit_des={
            "type": "function",
            "function": {
                "name": "setQuit",
                "description": "设置是否退出语音助手",
                "parameters": {
                    "type": "object",
                    "properties": {
                       "isQuit": {"type": "number","description": "退出为1,不退出为0",},
                    },
                    "required": ["isQuit"],
                },
            },
        }
def quit():
    global isquit
    print(f"isquit:{isquit}")
    re= True if isquit else False
    isquit=False
    return re
    

def runInTerminal(script):  
    # 作为字符串传递命令  
    try:  
        output = subprocess.check_output(script, shell=True, stderr=subprocess.STDOUT)  
        result = output.decode('utf-8')
        print(result)  # 需要解码成字符串 
    except subprocess.CalledProcessError as e:  
        print("Command failed with return code", e.returncode)  
        error=e.output.decode('utf-8')
        print("Error output:\n", error)  
        # 打印输出  
        result=f"Command failed with return code: {e.returncode}\nError output:\n{error}"
    return result
    
tool_runInTerminal_des={
            "type": "function",
            "function": {
                "name": "runInTerminal",
                "description": "对Mac电脑进行控制，执行脚本在终端，终端执行的结果是返回值",
                "parameters": {
                    "type": "object",
                    "properties": {
                       "script": {"type": "string","description": "执行的脚本或命令",},
                    },
                    "required": ["script"],
                },
            },
        }
#start switch role skill
tool_switchRole_des={
            "type": "function",
            "function": {
                "name": "switchRole",
                "description": "切换小新语音助手的角色",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "role": {"type": "string","description": "切换到的角色名称", "enum": ["日记助手", "音乐助手","系统控制助手","聊天助手","家庭教师"]},
                    },
                    "required": ["role"],
                },
            },
        }


def getTools():
    global tools
    return tools


def switchRole(role):
    global tools,messages
    if role=='日记助手':
        tools=[fun_newcontent_desc,
           fun_currentDatetime_desc,tool_addReminder_des,tool_removeReminder_des, tool_setLLMVersion_des,tool_CheckMessage_des,tool_switchRole_des]
        messages=[]
    elif role=='音乐助手':
        tools=[fun_playmusic_desc,fun_stopplay_desc,fun_pauseplay_desc,fun_unpauseplay_desc,
           fun_currentDatetime_desc,tool_addReminder_des,tool_removeReminder_des, tool_setLLMVersion_des,tool_CheckMessage_des,tool_switchRole_des,tool_setQuit_des]
        messages=[]
    elif role=='系统控制助手':
        tools=[tool_runInTerminal_des, tool_setLLMVersion_des,tool_switchRole_des]
        messages=[]
    elif role=='聊天助手':
        tools=[tool_setLLMVersion_des,tool_switchRole_des,tool_restart_self_des]
        messages=[]
    elif role=='家庭教师':
        tools=[fun_newcontent_desc,
           fun_currentDatetime_desc,tool_addReminder_des,tool_removeReminder_des, tool_setLLMVersion_des,tool_CheckMessage_des,tool_switchRole_des,tool_setQuit_des]
        messages=[]
    
    
    if role:
        return f"我现在是你的{role}了！"
    else:
        return "没有找到合适的助手。"
    
#end switch role skill

#start restart self skill
startfile='xiaoxin2_zh.py'
_isrestart=False
def restart_self(mainfile):
    global startfile,_isrestart
    setQuit(1)
    startfile=mainfile
    _isrestart=True
    return "收到，马上就好。"
    
tool_restart_self_des={
            "type": "function",
            "function": {
                "name": "restart_self",
                "description": "开始重启自身，特别指本语音助手重启时使用的方法",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "mainfile": {"type": "string","description": "py入口文件，固定为:xiaoxin2_zh.py"},
                    },
                    "required": ["mainfile"],
                },
            },
        }  
def isrestart():
    global startfile,_isrestart
    return _isrestart
def start():
    global startfile,_isrestart
    os.system(f'python {startfile}')  
#end restart self role skill

system_prompt=os.environ["sysprompt_zh-CN"]

def getSystemPrompt():
    return system_prompt
messages=[]
tools=[tool_setLLMVersion_des,tool_switchRole_des,tool_setQuit_des]
'''
tools=[fun_newcontent_desc,
           fun_currentDatetime_desc,tool_addReminder_des,tool_removeReminder_des, fun_playmusic_desc,fun_stopplay_desc,fun_pauseplay_desc,fun_unpauseplay_desc,
           fun_currentDatetime_desc,tool_addReminder_des,tool_removeReminder_des, tool_setLLMVersion_des,tool_CheckMessage_des,tool_switchRole_des,tool_setQuit_des,tool_restart_self_des,tool_openNewBot_des]
'''