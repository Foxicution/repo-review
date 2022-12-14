import openai
from streamlit import secrets
from json import loads
from generics import try_decorator

#TODO: Replace streamlit secrets with a method that works with FastAPI
openai.api_key = loads(secrets["openai_key"])['api_key']

@try_decorator
def get_completion(prompt: str) -> openai.Completion:
    return openai.Completion.create(model="text-davinci-002", prompt=prompt, max_tokens=700, temperature=0.1, top_p=1)

def main():
    prompt = """The following is a conversation with an AI assistant. The assistant is helpful, creative, clever, and very friendly.
    
    Human: Hello, who are you?
    AI: I am an AI created by OpenAI. How can I help you today?
    Human: I'd like to cancel my subscription.
    AI: I'm sorry to hear you want to cancel, you've been a great customer. Is there anything I can do to keep you as a customer?
    Human: I'm just not happy with the product.
    AI: I understand. Can you tell me more about why you aren't happy with the product?
    Human: It's too expensive.
    AI: I see. Our competitors are much more expensive. Would you be willing to pay a bit more for a better product?
    Human: No, I don't think so.
    AI: I understand. Do you have any suggestions for how we can improve the product?
    Human: Yes, I think you could add more features.
    AI: I see. What features would you like to see?
    Human: I'd like to see a dark mode option.
    AI: I see. Do you have any other suggestions?
    Human: No, that's it.
    AI: I understand. Thank you for your feedback. I will share it with my team. Is there anything else I can help you with today?
    Human: No, that's all.
    AI: Thank you for chatting with me. Have a great day!
    Human: You too.
    AI:"""
    print(get_completion(prompt))

if __name__ == '__main__':
    main()
