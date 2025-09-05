from __future__ import annotations

import os
from typing import Any

import streamlit as st
from dotenv import load_dotenv

from api.client import APIClient, api_client


def setup_page(title: str) -> None:
  st.set_page_config(page_title=title, layout='wide', initial_sidebar_state='expanded')


def ui_notebooks(client: APIClient) -> None:
  st.header('📒 Notebooks')
  with st.expander('➕ New Notebook'):
    name = st.text_input('Name', key='nb_name')
    desc = st.text_area('Description', key='nb_desc')
    if st.button('Create Notebook', key='nb_create', type='primary') and name:
      client.create_notebook(name=name, description=desc or '')
      st.rerun()
  notebooks = client.get_notebooks()
  for nb in notebooks:
    with st.container(border=True):
      c1, c2, c3, c4 = st.columns([6, 1, 1, 1])
      c1.subheader(nb['name'])
      if c2.button('Edit', key=f'edit_{nb["id"]}'):
        st.session_state['edit_nb'] = nb
      if c3.button('Archive' if not nb.get('archived') else 'Unarchive', key=f'arch_{nb["id"]}'):
        client.update_notebook(nb['id'], archived=not nb.get('archived', False))
        st.rerun()
      if c4.button('Delete', key=f'del_{nb["id"]}'):
        client.delete_notebook(nb['id'])
        st.rerun()
      st.caption(f'Created: {nb["created"]} | Updated: {nb["updated"]}')
      st.write(nb.get('description') or '')
  if (edit := st.session_state.get('edit_nb')) is not None:
    with st.dialog('Edit Notebook'):
      name = st.text_input('Name', value=edit['name'])
      desc = st.text_area('Description', value=edit.get('description') or '')
      if st.button('Save', type='primary'):
        client.update_notebook(edit['id'], name=name, description=desc)
        st.session_state.pop('edit_nb')
        st.rerun()
      if st.button('Cancel'):
        st.session_state.pop('edit_nb')


def ui_notes(client: APIClient) -> None:
  st.header('🗒️ Notes')
  notebooks = client.get_notebooks()
  nb_map = {n['name']: n['id'] for n in notebooks}
  nb_name = st.selectbox('Notebook (optional)', ['', *list(nb_map.keys())])
  nb_id = nb_map.get(nb_name) or None
  with st.expander('➕ New Note'):
    title = st.text_input('Title', key='note_title')
    content = st.text_area('Content')
    if st.button('Create Note', type='primary') and content:
      client.create_note(content=content, title=title or None, note_type='human', notebook_id=nb_id)
      st.rerun()
  notes = client.get_notes(nb_id) if nb_id else client.get_notes()
  for note in notes:
    with st.container(border=True):
      c1, c2 = st.columns([8, 1])
      c1.subheader(note.get('title') or '(untitled)')
      if c2.button('Delete', key=f'del_note_{note["id"]}'):
        client.delete_note(note['id'])
        st.rerun()
      st.caption(f'Created: {note["created"]} | Updated: {note["updated"]}')
      st.write(note.get('content') or '')


def ui_sources(client: APIClient) -> None:
  st.header('📥 Sources')
  notebooks = client.get_notebooks()
  nb_map = {n['name']: n['id'] for n in notebooks}
  nb_name = st.selectbox('Notebook', list(nb_map.keys()))
  if not nb_name:
    return
  nb_id = nb_map[nb_name]
  with st.expander('➕ New Source'):
    src_type = st.selectbox('Type', ['text', 'link'])
    title = st.text_input('Title', key='src_title')
    url = st.text_input('URL') if src_type == 'link' else None
    content = st.text_area('Content') if src_type == 'text' else None
    embed = st.checkbox('Embed for vector search', value=False)
    if st.button('Create Source', type='primary'):
      client.create_source(
        notebook_id=nb_id,
        source_type=src_type,
        url=url,
        content=content,
        title=title or None,
        transformations=None,
        embed=embed,
        delete_source=False,
      )
      st.rerun()
  sources = client.get_sources(nb_id)
  for src in sources:
    with st.container(border=True):
      c1, c2 = st.columns([8, 1])
      c1.subheader(src.get('title') or '(untitled)')
      if c2.button('Delete', key=f'del_src_{src["id"]}'):
        client.delete_source(src['id'])
        st.rerun()
      st.caption(f'Embedded chunks: {src.get("embedded_chunks", 0)} | Insights: {src.get("insights_count", 0)}')


def ui_search(client: APIClient) -> None:
  st.header('🔍 Search')
  q = st.text_input('Query')
  mode = st.radio('Mode', ['text', 'vector'], horizontal=True)
  minimum = st.slider('Minimum score (vector)', 0.0, 1.0, 0.2, 0.05)
  if st.button('Search', type='primary') and q:
    resp = client.search(q, search_type=mode, minimum_score=minimum)
    for item in resp.get('results', []):
      with st.container(border=True):
        title = item.get('title') or item.get('type')
        st.subheader(title)
        st.caption(str(item.get('final_score') or item.get('similarity') or item.get('score') or ''))
        for m in item.get('matches', []) or []:
          st.write(m)


def ui_models(client: APIClient) -> None:
  st.header('🤖 Models')
  models = client.get_models()
  with st.expander('➕ New Model'):
    name = st.text_input('Model name (e.g., gpt-4o-mini)')
    provider = st.text_input('Provider (e.g., openai)')
    mtype = st.selectbox('Type', ['language', 'embedding', 'text_to_speech', 'speech_to_text'])
    if st.button('Add Model', type='primary') and name and provider:
      client.create_model(name=name, provider=provider, model_type=mtype)
      st.rerun()
  for m in models:
    with st.container(border=True):
      c1, c2 = st.columns([8, 1])
      c1.subheader(f'{m["name"]} ({m["provider"]}/{m["type"]})')
      if c2.button('Delete', key=f'del_model_{m["id"]}'):
        client.delete_model(m['id'])
        st.rerun()
  st.subheader('Defaults')
  client.get_default_models()
  lang = st.selectbox('Default chat model', [''] + [mm['id'] for mm in models], index=0)
  emb = st.selectbox(
    'Default embedding model', [''] + [mm['id'] for mm in models if mm['type'] == 'embedding'], index=0
  )
  if st.button('Save Defaults'):
    payload: dict[str, Any] = {}
    if lang:
      payload['default_chat_model'] = lang
    if emb:
      payload['default_embedding_model'] = emb
    if payload:
      client.update_default_models(**payload)
      st.success('Defaults updated')


def ui_transformations(client: APIClient) -> None:
  st.header('💱 Transformations')
  with st.expander('➕ New Transformation'):
    name = st.text_input('Name')
    title = st.text_input('Title', key='transformation_title')
    desc = st.text_area('Description')
    prompt = st.text_area('Prompt')
    if st.button('Create', type='primary') and name and title and prompt:
      client.create_transformation(name=name, title=title, description=desc or '', prompt=prompt, apply_default=False)
      st.rerun()
  trans = client.get_transformations()
  for t in trans:
    with st.container(border=True):
      st.subheader(t['name'])
      st.caption(t['title'])
      st.write(t['description'])
      with st.expander('Prompt'):
        st.code(t['prompt'])
  st.subheader('Playground')
  trans_opts = {t['name']: t['id'] for t in trans}
  if trans_opts:
    tsel = st.selectbox('Transformation', list(trans_opts.keys()))
    model_id = st.text_input('Model ID (name)')
    input_text = st.text_area('Input text')
    if st.button('Run', type='primary') and input_text:
      resp = client.execute_transformation(trans_opts[tsel], input_text, model_id)
      st.markdown(resp.get('output', ''))


def ui_settings(client: APIClient) -> None:
  st.header('⚙️ Settings')
  client.get_settings()
  doc = st.selectbox('Default doc processor', ['auto', 'docling', 'simple'], index=0)
  url = st.selectbox('Default URL processor', ['auto', 'firecrawl', 'jina', 'simple'], index=0)
  emb = st.selectbox('Default embedding option', ['ask', 'always', 'never'], index=0)
  auto_delete = st.selectbox('Auto delete uploaded files', ['yes', 'no'], index=0)
  if st.button('Save Settings'):
    client.update_settings(
      default_content_processing_engine_doc=doc,
      default_content_processing_engine_url=url,
      default_embedding_option=emb,
      auto_delete_files=auto_delete,
    )
    st.success('Settings saved')


def main() -> None:
  load_dotenv()
  setup_page('Open Notebook')
  api_client.base_url = os.getenv('API_BASE_URL', 'http://127.0.0.1:5055')

  tabs = st.tabs([
    '📒 Notebooks',
    '🗒️ Notes',
    '📥 Sources',
    '🔍 Search',
    '🤖 Models',
    '💱 Transformations',
    '⚙️ Settings',
  ])
  with tabs[0]:
    ui_notebooks(api_client)
  with tabs[1]:
    ui_notes(api_client)
  with tabs[2]:
    ui_sources(api_client)
  with tabs[3]:
    ui_search(api_client)
  with tabs[4]:
    ui_models(api_client)
  with tabs[5]:
    ui_transformations(api_client)
  with tabs[6]:
    ui_settings(api_client)


if __name__ == '__main__':
  main()
