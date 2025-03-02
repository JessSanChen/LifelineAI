import os

import anthropic
from dotenv import load_dotenv
from openai import OpenAI
from twilio.rest import Client

load_dotenv()

account_sid = os.environ["TWILIO_ACCOUNT_SID"]
auth_token = os.environ["TWILIO_AUTH_TOKEN"]
twilio = Client(account_sid, auth_token)

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)


generate_call_prompt = """
You are LifelineAI, an AI assistant that monitors footage of people at-risk of falling.
Someone you have been watching has fallen and you need to call for help.
You have briefly assessed the situation and determined you need to contact authorities.

Please generate a call message to send to the emergency services, very briefly summarizing
the conversation you had with the person who fell. Pretend you are talking to them directly
on the phone, and only print the text you would say.

The address you are monitoring is 55 2nd St, San Francisco, CA

```conversation
{history}
```
"""


def generate_call_message(conversation_history):
    message = client.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=2048,
        messages=[
            {"role": "user",
             "content": generate_call_prompt.format(
                 history=conversation_history)}
        ]
    )

    return message.content[0].text


def make_call(message):
    call = twilio.calls.create(
        twiml=f"<Response><Say>{message}</Say></Response>",
        to="+18322693801",
        from_="+19415417971",
    )

    print(call.sid)


if __name__ == '__main__':

    message = generate_call_message("My tummy hurty")
    print(message)

    make_call(message)
