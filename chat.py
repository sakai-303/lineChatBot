import sqlalchemy
from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import sessionmaker, declarative_base
import tiktoken
from tiktoken.core import Encoding
import openai

system_message = ''

openai.api_key = ''

engine = sqlalchemy.create_engine('sqlite:///chat_log.sqlite3', echo=False)

Base = declarative_base()

session = sessionmaker(bind=engine)()


class ChatLog(Base):
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String)
    role = Column(String)
    message = Column(String)

    __tablename__ = 'chatlog'


def init():
    Base.metadata.create_all(bind=engine)


# エンドポイント
def chat(user_id: str, send_message: str):
    context: list = session.query(ChatLog.role, ChatLog.message).filter(ChatLog.user_id == user_id).limit(100).all()

    messages = make_messages(context, send_message)

    if not messages:
        # エラー文を送る処理
        return '文章量が多すぎます'

    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=messages
    )

    response_message = response.choices[0]["message"]["content"].strip()

    save_context(user_id=user_id, role='user', message=send_message)
    save_context(user_id=user_id, role='assistant', message=response_message)

    return response_message


def make_messages(context, send_message) -> list:
    context_message_list = [message_data[1] for message_data in context]

    encoding: Encoding = tiktoken.encoding_for_model("gpt-3.5-turbo")

    # コンテキストどこまで遡るか
    for i in range(len(context), 0, -1):
        tokens = encoding.encode(''.join(context_message_list[:i])+system_message+send_message)
        tokens_count = len(tokens)

        if tokens_count <= 2000:
            context_messages = [{'role': message_data[0], 'content': message_data[1]} for message_data in context]
            messages: list = [{'role': 'system', 'content': system_message}] + context_messages + [{'role': 'user', 'content': send_message}]

            return messages

    # コンテキスト抜いてもだめかチェック
    tokens = encoding.encode(system_message + send_message)
    tokens_count = len(tokens)

    if tokens_count <= 2000:
        messages: list = [{'role': 'system', 'content': system_message}] + [{'role': 'user', 'content': send_message}]
        return messages

    return []


def save_context(user_id: str, role: str, message: str):
    # 文脈を保存する処理
    chat_log = ChatLog()
    chat_log.user_id = user_id
    chat_log.role = role
    chat_log.message = message

    session.add(instance=chat_log)
    session.commit()


if __name__ == '__main__':
    print(chat(user_id='test_id', send_message='さっきなんの話したっけ'))
