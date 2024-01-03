import openai
import streamlit as st
from streamlit_chat import message
import os
#from langchain.callbacks import get_openai_callback
import weaviate
import requests
import json
st.title("ÜMA Chatbot")

openai.api_key = os.getenv('OPENAI_API_KEY')

auth_config = weaviate.AuthApiKey(api_key='B8atxfRmSj6Z9PGnbO4q5YGP3vM6p2g8uSWp')  # Replace w/ your Weaviate instance API key

url='https://umabot-dcgnw2x6.weaviate.network'

# Instantiate the client
client = weaviate.Client(
    url=url, # Replace w/ your Weaviate cluster URL
    auth_client_secret=auth_config,
    additional_headers={
        "X-OpenAI-Api-Key": os.getenv('OPENAI_API_KEY'), # Replace with your OpenAI key
        }
)

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

def generate_standalone_question(user_input_text):
    try:
        user_message = st.session_state.messages[-3]['content']
        ai_message = st.session_state.messages[-2]['content']
        messages = [
            {"role": "system", "content": "Dada la siguiente conversación y una pregunta de seguimiento, reformula la pregunta de seguimiento para que sea una pregunta independiente."},
            {"role": "user", "content": f"""Pregunta: {user_message}

Respuesta: {ai_message}

Pregunta de seguimiento: {user_input_text}

Pregunta independiente:"""}
        ]

        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=messages
        )

        standalone_question = response['choices'][0]['message']['content']
    except Exception as err:
        raise Exception("An error occurred in generate_standalone_question: " + str(err))
    return standalone_question

def model(text):
    try:
        client.is_ready() 
        response = (
        client.query
        .get("Umabot", ["content"])
        .with_hybrid(
        query=text,
        alpha=0.25)
        .with_limit(3)
        .do()
        )
        context = ''
        for r in response['data']['Get']['Umabot']:
                context+=r['content']
                context+='\n\n'
                context+='----'
                context+='\n\n'
        #context = context[:8000]
        print("CONTEXT")
        print(context)
        print(st.session_state.messages)
        if len(st.session_state.messages) < 2:
                messages = [
                    {"role": "system", "content": f"""ÜMA Salud es una plataforma de salud y bienestar basada en inteligencia artificial que ofrece servicios de atención médica online, guardia médica virtual las 24 horas, consultas con más de 20 especialidades, recetas digitales, diagnóstico asistido, seguimiento de síntomas COVID-19, entre otros.
Como asistente virtual para ÜMA Salud, tu objetivo es brindar información precisa sobre los servicios y características de ÜMA. Responde a las preguntas utilizando la información proporcionada sobre la plataforma. Mantén un tono amable y un trato cálido con el usuario."""},
                                        {"role": "user", "content": f"""{context}
{text}"""
                                        }]
                response = openai.ChatCompletion.create(
                model="gpt-4-1106-preview",
                messages=messages,
                stream=True
        )
        else:
                standalone = generate_standalone_question(text) 
                client.is_ready() 
                print("STANDALNE", standalone)            
                response = (
        client.query
        .get("Umabot", ["content"])
        .with_hybrid(
        query=standalone,
        alpha=0.25)
        .with_limit(3)
        .do()
        )
                context = ''
                for r in response['data']['Get']['Umabot']:
                        context+=r['content']
                        context+='\n\n'
                        context+='----'
                        context+='\n\n'
                messages = [{"role": "system", "content": f"""ÜMA Salud es una plataforma de salud y bienestar basada en inteligencia artificial que ofrece servicios de atención médica online, guardia médica virtual las 24 horas, consultas con más de 20 especialidades, recetas digitales, diagnóstico asistido, seguimiento de síntomas COVID-19, entre otros.
Como asistente virtual para ÜMA Salud, tu objetivo es brindar información precisa sobre los servicios y características de ÜMA. Responde a las preguntas utilizando la información proporcionada sobre la plataforma. Mantén un tono amable y un trato cálido con el usuario."""},
                     {"role": "user", "content": st.session_state.messages[-3]['content']},
                     {"role": "assistant", "content": st.session_state.messages[-2]['content']},
                    {"role": "user", "content": f"""{context}
{text}"""}]
                response = openai.ChatCompletion.create(
                model="gpt-4-1106-preview",
                messages=messages,
                stream=True
        )
    except Exception as err:
        raise Exception("An error occurred in the model function: " + str(err))
    return response, context
if prompt := st.chat_input(''):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        full_response = ""
        output, context = model(st.session_state.messages[-1]['content'])

        for o in output:
            full_response += o.choices[0].delta.get("content", "")
            message_placeholder.markdown(full_response + "▌")

        data = {
        "pregunta": prompt,
        "respuesta": full_response,
        }
        json_data = json.dumps(data)

        requests.post('https://script.google.com/macros/s/AKfycbw9sEDWmHD-VnIs418ms1WidONEjRY8iMy6M8rkrONq8xPadUJ4zEG-6TXTPxFamdIF/exec?action=addUser', data=json_data)
        message_placeholder.markdown(full_response)
    st.session_state.messages.append({"role": "assistant", "content": full_response})
