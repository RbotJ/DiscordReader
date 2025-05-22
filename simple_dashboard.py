"""
Simple monitoring dashboard that uses PostgreSQL for data.
"""
import streamlit as st
from datetime import datetime, timedelta
import pandas as pd

from common.db import db
from common.db_models import DiscordMessageModel, SetupModel

def load_recent_messages():
    """Load recent Discord messages from database"""
    messages = DiscordMessageModel.query.order_by(
        DiscordMessageModel.timestamp.desc()
    ).limit(100).all()

    return pd.DataFrame([{
        'id': msg.message_id,
        'content': msg.content,
        'author': msg.author,
        'timestamp': msg.timestamp
    } for msg in messages])

def main():
    st.title('A+ Trading Monitor')

    # Load and display recent messages
    messages_df = load_recent_messages()

    if not messages_df.empty:
        st.subheader('Recent Messages')
        st.dataframe(messages_df)
    else:
        st.info('No recent messages found')

if __name__ == '__main__':
    main()