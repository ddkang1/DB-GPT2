#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import os
import uuid
import json
import time
import gradio as gr
import datetime
import requests
from urllib.parse import urljoin
from pilot.configs.model_config import DB_SETTINGS
from pilot.server.vectordb_qa import KnownLedgeBaseQA
from pilot.connections.mysql import MySQLOperator
from pilot.vector_store.extract_tovec import get_vector_storelist, load_knownledge_from_doc, knownledge_tovec_st

from pilot.configs.model_config import LOGDIR, VICUNA_MODEL_SERVER, LLM_MODEL, DATASETS_DIR

from pilot.conversation import (
    default_conversation,
    conv_templates,
    conversation_types,
    SeparatorStyle
)

from fastchat.utils import (
    build_logger,
    server_error_msg,
    violates_moderation,
    moderation_msg
)

from pilot.server.gradio_css import code_highlight_css
from pilot.server.gradio_patch import Chatbot as grChatbot

logger = build_logger("webserver", LOGDIR + "webserver.log")
headers = {"User-Agent": "dbgpt Client"}

no_change_btn = gr.Button.update()
enable_btn = gr.Button.update(interactive=True)
disable_btn = gr.Button.update(interactive=True)

enable_moderation = False
models = []
dbs = []
vs_list = ["New Knowledge Base"] + get_vector_storelist()

priority = {
    "vicuna-13b": "aaa"
}

def get_simlar(q):
    
    docsearch = knownledge_tovec_st(os.path.join(DATASETS_DIR, "plan.md"))
    docs = docsearch.similarity_search_with_score(q, k=1)

    contents = [dc.page_content for dc, _ in docs]
    return "\n".join(contents)
    
    

def gen_sqlgen_conversation(dbname):
    mo = MySQLOperator(
        **DB_SETTINGS
    )

    message = ""

    schemas = mo.get_schema(dbname)
    for s in schemas:
        message += s["schema_info"] + ";"
    return f"Schema information for database {dbname} is as follows: {message}\n"

def get_database_list():
    mo = MySQLOperator(**DB_SETTINGS)
    return mo.get_db_list()

get_window_url_params = """
function() {
    const params = new URLSearchParams(window.location.search);
    url_params = Object.fromEntries(params);
    console.log(url_params);
    gradioURL = window.location.href
    if (!gradioURL.endsWith('?__theme=dark')) {
        window.location.replace(gradioURL + '?__theme=dark');
    }
    return url_params;
    }
"""
def load_demo(url_params, request: gr.Request):
    logger.info(f"load_demo. ip: {request.client.host}. params: {url_params}")

    dbs = get_database_list()
    dropdown_update = gr.Dropdown.update(visible=True)
    if dbs:
        gr.Dropdown.update(choices=dbs)

    state = default_conversation.copy()
    return (state,
            dropdown_update,
            gr.Chatbot.update(visible=True),
            gr.Textbox.update(visible=True),
            gr.Button.update(visible=True),
            gr.Row.update(visible=True),
            gr.Accordion.update(visible=True))

def get_conv_log_filename():
    t = datetime.datetime.now()
    name = os.path.join(LOGDIR, f"{t.year}-{t.month:02d}-{t.day:02d}-conv.json")
    return name


def regenerate(state, request: gr.Request):
    logger.info(f"regenerate. ip: {request.client.host}")
    state.messages[-1][-1] = None
    state.skip_next = False
    return (state, state.to_gradio_chatbot(), "") + (disable_btn,) * 5

def clear_history(request: gr.Request):
    logger.info(f"clear_history. ip: {request.client.host}")
    state = None
    return (state, [], "") + (disable_btn,) * 5


def add_text(state, text, request: gr.Request):
    logger.info(f"add_text. ip: {request.client.host}. len: {len(text)}")
    if len(text) <= 0:
        state.skip_next = True
        return (state, state.to_gradio_chatbot(), "") + (no_change_btn,) * 5
    if args.moderate:
        flagged = violates_moderation(text)
        if flagged:
            state.skip_next = True
            return (state, state.to_gradio_chatbot(), moderation_msg) + (
                no_change_btn,) * 5

    text = text[:1536]  # Hard cut-off
    state.append_message(state.roles[0], text)
    state.append_message(state.roles[1], None)
    state.skip_next = False
    return (state, state.to_gradio_chatbot(), "") + (disable_btn,) * 5

def post_process_code(code):
    sep = "\n```"
    if sep in code:
        blocks = code.split(sep)
        if len(blocks) % 2 == 1:
            for i in range(1, len(blocks), 2):
                blocks[i] = blocks[i].replace("\\_", "_")
        code = sep.join(blocks)
    return code

def http_bot(state, mode, db_selector, temperature, max_new_tokens, request: gr.Request):
    start_tstamp = time.time()
    model_name = LLM_MODEL

    dbname = db_selector
    # TODO The request here needs to be concatenated with the existing knowledge base, so that it answers based on the existing knowledge base. Therefore, the prompt needs to be further optimized.
    if state.skip_next:
        # This generate call is skipped due to invalid inputs
        yield (state, state.to_gradio_chatbot()) + (no_change_btn,) * 5
        return

   
    if len(state.messages) == state.offset + 2:
        # First round of conversation requires adding a prompt
        
        template_name = "conv_one_shot"
        new_state = conv_templates[template_name].copy()
        new_state.conv_id = uuid.uuid4().hex
        
        query = state.messages[-2][1]

        # Add context hints to the prompt, have conversations based on existing knowledge, should context hints be added in the first round or in every round?
        # If the user's questions span a wide range, a prompt should be added in each round.
        if db_selector:
            new_state.append_message(new_state.roles[0], gen_sqlgen_conversation(dbname) + query)
            new_state.append_message(new_state.roles[1], None)
            state = new_state
        else:
            new_state.append_message(new_state.roles[0], query)
            new_state.append_message(new_state.roles[1], None)
            state = new_state

    if mode == conversation_types["default_knownledge"] and not db_selector:
        query = state.messages[-2][1]
        knqa = KnownLedgeBaseQA()
        state.messages[-2][1] = knqa.get_similar_answer(query)
        

    prompt = state.get_prompt()
    
    skip_echo_len = len(prompt.replace("</s>", " ")) + 1

    # Make requests
    payload = {
        "model": model_name,
        "prompt": prompt,
        "temperature": float(temperature),
        "max_new_tokens": int(max_new_tokens),
        "stop": state.sep if state.sep_style == SeparatorStyle.SINGLE else state.sep2,
    }
    logger.info(f"Requert: \n{payload}")

    state.messages[-1][-1] = "▌"
    yield (state, state.to_gradio_chatbot()) + (disable_btn,) * 5

    try:
        # Stream output
        response = requests.post(urljoin(VICUNA_MODEL_SERVER, "generate_stream"),
            headers=headers, json=payload, stream=True, timeout=20)
        for chunk in response.iter_lines(decode_unicode=False, delimiter=b"\0"):
            if chunk:
                data = json.loads(chunk.decode())
                if data["error_code"] == 0:
                    output = data["text"][skip_echo_len:].strip()
                    output = post_process_code(output)
                    state.messages[-1][-1] = output + "▌"
                    yield (state, state.to_gradio_chatbot()) + (disable_btn,) * 5
                else:
                    output = data["text"] + f" (error_code: {data['error_code']})"
                    state.messages[-1][-1] = output
                    yield (state, state.to_gradio_chatbot()) + (disable_btn, disable_btn, disable_btn, enable_btn, enable_btn)
                    return

    except requests.exceptions.RequestException as e:
        state.messages[-1][-1] = server_error_msg + f" (error_code: 4)"
        yield (state, state.to_gradio_chatbot()) + (disable_btn, disable_btn, disable_btn, enable_btn, enable_btn)
        return

    state.messages[-1][-1] = state.messages[-1][-1][:-1]
    yield (state, state.to_gradio_chatbot()) + (enable_btn,) * 5

    # Record running logs
    finish_tstamp = time.time()
    logger.info(f"{output}")

    with open(get_conv_log_filename(), "a") as fout:
        data = {
            "tstamp": round(finish_tstamp, 4),
            "type": "chat",
            "model": model_name,
            "start": round(start_tstamp, 4),
            "finish": round(start_tstamp, 4),
            "state": state.dict(),
            "ip": request.client.host,
        }
        fout.write(json.dumps(data) + "\n")

block_css = (
    code_highlight_css
    + """
pre {
    white-space: pre-wrap;       /* Since CSS 2.1 */
    white-space: -moz-pre-wrap;  /* Mozilla, since 1999 */
    white-space: -pre-wrap;      /* Opera 4-6 */
    white-space: -o-pre-wrap;    /* Opera 7 */
    word-wrap: break-word;       /* Internet Explorer 5.5+ */
}
#notice_markdown th {
    display: none;
}
    """
)

def change_tab(tab):
    pass

def change_mode(mode):
    if mode in ["Default Knowledge Base Conversation", "LLM Native Conversation"]:
        return gr.update(visible=False)
    else:
        return gr.update(visible=True)


def build_single_model_ui():

    notice_markdown = """
    # DB-GPT

    [DB-GPT](https://github.com/csunny/DB-GPT) is an experimental open-source application based on [FastChat](https://github.com/lm-sys/FastChat) and uses vicuna-13b as the underlying model. Moreover, this program combines langchain and llama-index for In-Context Learning based on existing knowledge bases to enhance its database-related knowledge. It can perform tasks such as SQL generation, SQL diagnosis, and database knowledge question-answering. Overall, it is a complex and innovative AI tool for databases. If you have any specific questions about how to use or implement DB-GPT in your work, please contact me. I will do my best to help, and everyone is welcome to participate in the project and do something interesting.
    """
    learn_more_markdown = """ 
        ### Licence
        The service is a research preview intended for non-commercial use only. subject to the model [License](https://github.com/facebookresearch/llama/blob/main/MODEL_CARD.md) of Vicuna-13B 
    """

    state = gr.State()
    gr.Markdown(notice_markdown, elem_id="notice_markdown")

    with gr.Accordion("Parameters", open=False, visible=False) as parameter_row:
        temperature = gr.Slider(
            minimum=0.0,
            maximum=1.0,
            value=0.7,
            step=0.1,
            interactive=True,
            label="Temperature",
        )

        max_output_tokens = gr.Slider(
            minimum=0,
            maximum=1024,
            value=512,
            step=64,
            interactive=True,
            label="Maximum Output Token Count",
        )
    tabs = gr.Tabs() 
    with tabs:
        with gr.TabItem("SQL Generation and Diagnosis", elem_id="SQL"):
        # TODO A selector to choose database
            with gr.Row(elem_id="db_selector"):
                db_selector = gr.Dropdown(
                    label="Please select a database",
                    choices=dbs,
                    value=dbs[0] if len(models) > 0 else "",
                    interactive=True,
                    show_label=True).style(container=False) 

        with gr.TabItem("Knowledge Q&A", elem_id="QA"):
            
            mode = gr.Radio(["LLM Native Conversation", "Default Knowledge Base Conversation", "Add New Knowledge Base Conversation"], show_label=False, value="LLM Native Conversation")
            vs_setting = gr.Accordion("Configure Knowledge Base", open=False)
            mode.change(fn=change_mode, inputs=mode, outputs=vs_setting)
            with vs_setting:
                vs_name = gr.Textbox(label="New Knowledge Base Name", lines=1, interactive=True)
                vs_add = gr.Button("Add as New Knowledge Base")
                with gr.Column() as doc2vec:
                    gr.Markdown("Add files to the knowledge base")
                    with gr.Tab("Upload Files"):
                        files = gr.File(label="Add files", 
                                        file_types=[".txt", ".md", ".docx", ".pdf"],
                                        file_count="multiple",
                                        show_label=False
                                        )

                        load_file_button = gr.Button("Upload and Load into Knowledge Base")
                    with gr.Tab("Upload Folders"):
                        folder_files = gr.File(label="Add files",
                                            file_count="directory",
                                            show_label=False)
                        load_folder_button = gr.Button("Upload and Load into Knowledge Base")
    

    with gr.Blocks():
        chatbot = grChatbot(elem_id="chatbot", visible=False).style(height=550)
        with gr.Row():
            with gr.Column(scale=20):
                textbox = gr.Textbox(
                    show_label=False,
                    placeholder="Enter text and press ENTER",
                    visible=False,
                ).style(container=False)          
            with gr.Column(scale=2, min_width=50):
                send_btn = gr.Button(value="Send", visible=False) 

    with gr.Row(visible=False) as button_row:
        regenerate_btn = gr.Button(value="Regenerate", interactive=False)
        clear_btn = gr.Button(value="Clear", interactive=False)


    gr.Markdown(learn_more_markdown)

    btn_list = [regenerate_btn, clear_btn]
    regenerate_btn.click(regenerate, state, [state, chatbot, textbox] + btn_list).then(
        http_bot,
        [state, mode, db_selector, temperature, max_output_tokens],
        [state, chatbot] + btn_list,
    )
    clear_btn.click(clear_history, None, [state, chatbot, textbox] + btn_list)
    
    textbox.submit(
        add_text, [state, textbox], [state, chatbot, textbox] + btn_list
    ).then(
        http_bot,
        [state, mode, db_selector, temperature, max_output_tokens],
        [state, chatbot] + btn_list,
    )

    send_btn.click(
        add_text, [state, textbox], [state, chatbot, textbox] + btn_list
    ).then(
        http_bot,
        [state, mode, db_selector, temperature, max_output_tokens],
        [state, chatbot] + btn_list
    )

    return state, chatbot, textbox, send_btn, button_row, parameter_row


def build_webdemo():
    with gr.Blocks(
        title="Database Intelligent Assistant",
        # theme=gr.themes.Base(),
        theme=gr.themes.Default(),
        css=block_css,
    ) as demo:
        url_params = gr.JSON(visible=False)
        (
            state,
            chatbot,
            textbox,
            send_btn,
            button_row,
            parameter_row,
        ) = build_single_model_ui()

        if args.model_list_mode == "once":
            demo.load(
                load_demo,
                [url_params],
                [
                    state,
                    chatbot,
                    textbox,
                    send_btn,
                    button_row,
                    parameter_row,
                ],
                _js=get_window_url_params,
            )
        else:
            raise ValueError(f"Unknown model list mode: {args.model_list_mode}")
    return demo

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", type=str, default="0.0.0.0")
    parser.add_argument("--port", type=int)
    parser.add_argument("--concurrency-count", type=int, default=10)
    parser.add_argument(
        "--model-list-mode", type=str, default="once", choices=["once", "reload"]
    )
    parser.add_argument("--share", default=False, action="store_true")
    parser.add_argument(
        "--moderate", action="store_true", help="Enable content moderation"
    )
    args = parser.parse_args()
    logger.info(f"args: {args}")

    dbs = get_database_list()
    logger.info(args)
    demo = build_webdemo()
    demo.queue(
        concurrency_count=args.concurrency_count, status_update_rate=10, api_open=False
    ).launch(
        server_name=args.host, server_port=args.port, share=args.share, max_threads=200,
    )