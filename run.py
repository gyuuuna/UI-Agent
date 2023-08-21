## set ANDROID_HOME=C:\Users\cufft\Downloads\platform-tools_r34.0.4-windows

import os
import time
import subprocess

from com.dtmilano.android.viewclient import ViewClient
import openai
from hangul_utils import split_syllables
from dotenv import load_dotenv

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")
if openai.api_key == None:
    raise ValueError(
        "OpenAI API key not found. Please set the OPENAIAPI environment variable."
    )

chatgpt = 'gpt-3.5-turbo'
gpt4 = 'gpt-4'

prompt_template = """
You are an agent controlling an android phone screen. You are given:

    (1) objectives that you are trying to achieve
	(2) log of the previous actions you've done to achieve the objectives.
    (3) the elements in your phone screen, and the actions you can do with the elements.

You can issue these commands:
	CHECK X : check on the checkbox with id X
	UNCHECK X : uncheck on the checkbox with id X
	CLICK X : click on a given element with id X
	SCROLL-UP X : scroll up one page on the element with id X
	SCROLL-DOWN X : scroll down one page on the element with id X
	LONG-CLICK X : long-click on a given element with id X
	SELECT X : select on a given element with id X
	UNSELECT X : select on a given element with id X
	TYPE X "TEXT" : type the specified text into the element with id X
 
 And if you think you already achieved the objective, you can issue
    STOP : quit

The format of the browser content is highly simplified; all formatting elements are stripped.
Interactive elements are represented like this:

		<(class) id=(id)> (description) | content: (content) | enabled actions: (action1, action2, ... actionN) </link>

Based on your given objective, issue whatever command you believe will get you closest to achieving your goal.
Interact with the elements on the screen to achieve your objective.
Don't try to interact with elements that you can't see.
Then, tell me the reason why you choosed the action.

Here are some examples:

EXAMPLE 1:
CURRENT SCREEN CONTENT:
------------------
<Button id=1> submit-button | content: 제출 | enabled actions: CLICK, LONG-CLICK </Button>
<Button id=2> close-button | content: 종료 | enabled actions: CLICK, LONG-CLICK </Button>
------------------
OBJECTIVE: 사이트에 가능한 시간과 요일 (20:00, 월요일)을 적고 제출합니다.
PREVIOUS LOG:
- [Action] CLICK 6 [Reason] I clicked the 'Next' button to continue.
- [Action] TYPE 3 "20:00 monday" [Reason] I wrote down the given time and the day of the week to the type form, to notice the enable time.
YOUR COMMAND:
CLICK 1 // I clicked submit-button instead of the close-button, because I have to submit the text I wrote, according to the objective.

EXAMPLE 2:
CURRENT SCREEN CONTENT:
------------------
<LinearLayout id=31> notice_layout | content:  공지사항 Video-llama 경기 해설, Highlight 캡처에 활용박윤아 버튼 | enabled actions: CLICK, TYPE </LinearLayout>
   <RelativeLayout id=32> notice_content_container  | enabled actions: CLICK, LONG-CLICK, TYPE </RelativeLayout>
    <ImageView id=33> expand_button | content:  공지 펼치기 | enabled actions: CLICK, TYPE </ImageView>
  <FrameLayout id=34> media_send_layout | content:  미디어 전송 키보드 열기 버튼 | enabled actions: CLICK, TYPE </FrameLayout>
  <LinearLayout id=35> ii_message_edit_text  | enabled actions: CLICK, TYPE </LinearLayout>
   <MultiAutoCompleteTextView id=36> message_edit_text  | enabled actions: CLICK, LONG-CLICK, TYPE </MultiAutoCompleteTextView>
  <ewGroup id=37> emoticon_button_layout | content:  이모티콘 키보드 열기 버튼 | enabled actions: CLICK, TYPE </ewGroup>
  <FrameLayout id=38> search_sharp_layout | content:  샵검색 열기 버튼 | enabled actions: CLICK, TYPE </FrameLayout>
------------------
OBJECTIVE: Send 카카오톡 message, '안녕'
PREVIOUS LOG:
There is no command done yet.
YOUR COMMAND:
TYPE 36 "안녕" // I chose to type "카카오톡 안녕" into the message_edit_text field (id 36), because this is the message

----

The current screen content, objective, and previous logs follow. Reply with your next command to the browser.
You must answer in the form "(Action) // (Reason you chose the action)"

CURRENT SCREEN CONTENT:
------------------
$screen_content
------------------
OBJECTIVE: $objective
PREVIOUS LOG: $previous_log
YOUR COMMAND:
"""

def extract_properties(view):
    # properties = [
    #    "checkable", "checked", "clickable", "focusable",
    #    "focused", "scrollable", "long-clickable", "password", "selected"
    # ]

    extracted_properties = ''
    
    if getattr(view, 'checkable')():
        if getattr(view, 'checked')():
            extracted_properties += 'UNCHECK, '
        else:
            extracted_properties += 'CHECK, '
    if getattr(view, 'clickable')():
        extracted_properties += 'CLICK, '
    if getattr(view, 'scrollable')():
        extracted_properties += 'SCROLL-UP, SCROLL-DOWN, '
    if getattr(view, 'long-clickable')():
        extracted_properties += 'LONG-CLICK, '
    if (getattr(view, 'focusable')() or getattr(view, 'password')()) and getattr(view, 'clickable')() and getattr(view, 'enabled')():
        extracted_properties += 'TYPE, '
    if getattr(view, 'selected')():
        extracted_properties += 'UNSELECT, '
    
    if extracted_properties != '':
        extracted_properties = f'| enabled actions: {extracted_properties}'[:-2]
    return extracted_properties


def extract(view: ViewClient):
    view_class = view.getClass()
    # if not str(view_class).startswith('android.widget.'):
    #    return ''
    
    content_desc = view.getContentDescription().replace('\n', ' ')
    text = view.getText().replace('\n', ' ')
    id = view.getId()
    
    # if not content_desc and not text and not id:
    #    return ''
    
    unique_id = view.getUniqueId()[9:]
    view_class = view_class[15:]
    
    if id:
        loc = id.find('/')+1
        id = f'{id[loc:]}'
    if text != '' or content_desc != '':
        content = f'| content: {text} {content_desc}'
    else: content = ''
    
    properties = extract_properties(view)
    item_desc = f"<{view_class} id={unique_id}> {id} {content} {properties} </{view_class}>\n"
    
    return item_desc

def traverse_view(view, depth=0):
    view_str = ''
    if view:
        view_str += extract(view)
        
        children = view.getChildren()
        if children:
            for child in children:
                view_str += ' '*depth + traverse_view(child, depth+1)
    
    return view_str

def run():
    view_client = ViewClient(*ViewClient.connectToDeviceOrExit())
    log = []
    objective = input('This is your Android Phone Assistant, AndBot. What is your objective? ')
    
    def get_gpt_command(screen_content):
        prompt = prompt_template
        prompt = prompt.replace('$screen_content', screen_content)
        prompt = prompt.replace('$objective', objective)
        
        if len(log)==0:
            log_text = 'No action done yet.'
        else:
            log_text = ''
            for command in log:
                log_text += f'- [Action] {command[0]} [Reason] {command[1]}\n'
        prompt = prompt.replace('$previous_log', log_text)
        
        response = openai.ChatCompletion.create(
            model=chatgpt,
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.5, max_tokens=1000
        ).choices[0].message.content
        print(response)
        command, reason = response.split(' // ')
        return command, reason
    
    def find_view(unique_id, view):
        if hasattr(view, 'getUniqueId') and view.getUniqueId() == 'id/no_id/'+unique_id:
            return view
        children = view.getChildren()
        if children:
            for child in children:
                found_view = find_view(unique_id, child)
                if found_view:
                    return found_view
        return None
    
    def execute(action, unique_id, *input_text):
        view_client.dump()
        target_view = find_view(unique_id, view_client.getRoot())
        if not target_view:
            return
        if input_text:
            input_text = ' '.join(input_text)
            input_text = input_text.strip('"')
            print("Type in "+input_text)
        
        action = action.lower()
        if action == "check":
            target_view.touch()
        elif action == "uncheck":
            target_view.touch()
        elif action == "click":
            target_view.touch()
        elif action == "long-click":
            target_view.longTouch()
        elif action == "select":
            target_view.touch()
        elif action == "unselect":
            target_view.touch()
        elif action == "type":
            target_view.touch()
            
            kor_chars = "ㅂㅈㄷㄱㅅㅛㅕㅑㅐㅔㅁㄴㅇㄹㅎㅗㅓㅏㅣ"
            eng_chars = "QWERTYUIOPASDFGHJKLZXCVBNM".lower()
            
            if '가' <= input_text[0] <= '힣':
                adb_command = 'adb shell ime set com.google.android.inputmethod.latin/com.android.inputmethod.latin.LatinIME'
                subprocess.run(adb_command, shell=True, capture_output=True, text=False)
                time.sleep(2)
                
                eng_input_text = ''
                for char in input_text:
                    for seg in split_syllables(char):
                        index = kor_chars.index(seg)
                        eng_input_text += eng_chars[index]
                adb_command = f"adb shell input text '{eng_input_text}'"
                subprocess.run(adb_command, shell=True, capture_output=True, text=True)
                
                adb_command = 'adb shell ime set com.samsung.android.honeyboard/.service.HoneyBoardService'
                subprocess.run(adb_command, shell=True, capture_output=True, text=False)
                time.sleep(2)
                
            else:
                adb_command = f"adb shell input text '{input_text}'" 
                subprocess.run(adb_command, shell=True, capture_output=True, text=True)
                
        
    try:
        while True:
            # view_client = ViewClient(*ViewClient.connectToDeviceOrExit())
            view_client.dump()
            root_view = view_client.getRoot()
            traversed_content = traverse_view(root_view)
            print('-------------------- Your View --------------------')
            print(traversed_content)
            print('---------------------------------------------------')
            
            command, reason = get_gpt_command(traversed_content)
            print('Suggested command: '+command)
            print('Reason: '+reason)
            
            if command.startswith('STOP'):
                exit(0)
            
            execute_flag = input('Execute or not? Press Y/N: ')
            if execute_flag in ['Y', 'y']:
                try:
                    execute(*command.split(' '))
                    log.append((command, 'Y', reason+': Succesfully executed'))
                except:
                    log.append((command, reason+': Failed, could not execute'))
                    continue
            else:
                log.append((command, reason+': Failed, wrong choice'))
                continue
            
    except KeyboardInterrupt:
        exit(0)
            
def main():
    run_count = 20
    while(run_count > 0):
        run()
        run_count -= 1
    
if __name__=='__main__':
    main()