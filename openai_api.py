import openai

class ChatGPT:
    def __init__(self, engine="gpt-3.5-turbo", system="You are a helpful assistant."):
        self.engine = engine
        self.system = system
        self.messages = [{"role": "system", "content": self.system}]

    def chat(self, message, reset=False):
        # print(self.messages)
        self.messages.append({"role": "user", "content": message})
        
        # print(self.messages)
        if reset:
            message = {"role":"user", "content": self.messages}
            messages = [{"role": "system", "content": self.system}].append(message)
        else:
            messages = self.messages

        response = openai.ChatCompletion.create(
            model = self.engine,
            messages = messages,
        )
        answer = response.choices[0].message.content
        self.messages.append({"role": "assistant", "content": answer})
        return answer

class GPT:
    def __init__(self, engine, prompt):
        self.engine = engine
        self.prompt = prompt

    def chat(self, message):
        response = openai.Completion.create(
            engine=self.engine, 
            prompt=f'{self.prompt}\n{message}',
            temperature=0.1, 
            max_tokens=1000
        )
        answer = response.choices[0]['text']
        return answer 