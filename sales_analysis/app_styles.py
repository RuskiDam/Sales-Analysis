class AppStyles:
    STREAMLIT = """
    <style>
    .block-container {
        max-width: 1280px;
        padding-top: 2rem;
    }
    section[data-testid="stSidebar"] {
        min-width: 260px;
        width: 260px;
    }
    section[data-testid="stSidebar"] > div:first-child {
        position: fixed;
        top: 0;
        bottom: 0;
        width: 260px;
    }
    div[data-testid="stHorizontalBlock"] {
        gap: 14px;
    }
    div[data-testid="stButton"] > button {
        border-radius: 4px;
        height: 42px;
        line-height: 1.2;
    }
    section[data-testid="stSidebar"] div[data-testid="stButton"] > button {
        height: 112px;
        margin-bottom: 10px;
        min-width: 210px;
        white-space: pre-line;
        width: 210px;
    }
    section[data-testid="stSidebar"] div[data-testid="stButton"] > button p {
        font-size: 20px;
        font-weight: 700;
        line-height: 1.25;
    }
    .nav-marker {
        border-radius: 4px;
        height: 112px;
        margin-bottom: 10px;
        min-width: 6px;
        width: 6px;
    }
    .nav-marker-active {
        background: #0969da;
    }
    div[data-testid="stMetricLabel"] p {
        font-size: 0.9rem;
        font-weight: 700;
    }
    div[data-testid="stDataFrame"] {
        border: 1px solid #d0d7de;
        border-radius: 6px;
        overflow: hidden;
    }
    .ai-page {
        max-width: 900px;
        margin: 0 auto;
    }
    .ai-page h1 {
        margin-bottom: 0.25rem;
    }
    .ai-empty-state {
        min-height: 260px;
        display: flex;
        align-items: center;
        justify-content: center;
        text-align: center;
    }
    .ai-empty-state h2 {
        color: #24292f;
        font-size: 2rem;
        font-weight: 650;
        letter-spacing: 0;
        line-height: 1.2;
        margin: 0;
    }
    div[data-testid="stChatMessage"] {
        border-radius: 6px;
        margin: 0.5rem auto;
        max-width: 900px;
    }
    div[data-testid="stChatInput"] {
        max-width: 900px;
        margin: 0 auto;
    }
    h1 {
        letter-spacing: 0;
    }
    </style>
    """
