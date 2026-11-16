import React, { useEffect, useRef, useState } from 'react';
import {
  ArrowRight, ArrowUp, BookOpen, Check, ChevronDown, CircleHelp, Code2, Copy,
  Lightbulb, Menu, MessageSquare, MoreHorizontal, PanelLeftClose, PanelLeftOpen,
  Plus, Search, Sparkles, X, Zap
} from 'lucide-react';
import { sendChatMessage, fetchConversation, fetchConversations, fetchModels } from './chatApi';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

const CHAT_URL = '/chat/';
const DEFAULT_MODEL = 'deepseek-ai/deepseek-v4.1-flash';
const fallbackModels = [
  { id: DEFAULT_MODEL, name: 'DeepSeek V4.1 Flash', provider: 'NVIDIA' },
  { id: 'z-ai/glm-5.3-flash', name: 'GLM-5.3 Flash', provider: 'NVIDIA' },
];
const starters = [
  { icon: Lightbulb, title: 'Think something through', description: 'Explore an idea from every angle', prompt: 'Help me think through a new idea.' },
  { icon: Code2, title: 'Build something', description: 'From a snippet to a full project', prompt: 'Help me build a simple web app.' },
  { icon: BookOpen, title: 'Learn a new concept', description: 'Understand something, step by step', prompt: 'Explain how neural networks learn.' },
];
const csrfToken = () => decodeURIComponent(document.cookie.split('; ').find(c => c.startsWith('csrftoken='))?.split('=')[1] || '');
const idFromUrl = () => new URLSearchParams(window.location.search).get('conversation');

function ModelSelect({ model, setModel, disabled, availableModels }) {
  const [open, setOpen] = useState(false);
  const ref = useRef(null);
  useEffect(() => {
    const close = e => { if (!ref.current?.contains(e.target)) setOpen(false); };
    document.addEventListener('pointerdown', close);
    return () => document.removeEventListener('pointerdown', close);
  }, []);
  return <div className="model-select" ref={ref}>
    <button type="button" disabled={disabled || availableModels.length===0} className="model-trigger" onClick={() => setOpen(!open)} aria-expanded={open}><span className="model-glyph"><Sparkles size={15}/></span>{availableModels.find(m=>m.id===model)?.name || model}<ChevronDown size={15}/></button>
    {open && <div className="model-dropdown"><div className="dropdown-label">CHOOSE A MODEL</div>{availableModels.map(m =>
      <button key={m.id} type="button" className={'model-option '+(model===m.id?'selected':'')} onClick={() => { setModel(m.id); setOpen(false); }}>
        <span className="model-color" style={{background:m.id.startsWith('z-ai')?'#a778ed':'#6547d2'}}/><span><strong>{m.name}</strong><small>{m.provider}</small></span>{model===m.id&&<Check size={15}/>}
      </button>)}</div>}
  </div>;
}

function Composer({ model, setModel, onSend, pending, text, setText, availableModels }) {
  const submit = event => {
    event?.preventDefault();
    if (pending || !text.trim()) return;
    onSend(text.trim());
  };
  return <form className="composer" onSubmit={submit}>
    <textarea rows={2} value={text} disabled={pending} onChange={e=>setText(e.target.value)}
      onKeyDown={e=>{if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();submit();}}}
      aria-label="Message" placeholder="Ask anything..."/>
    <div className="composer-toolbar">
      <div className="composer-left"><ModelSelect model={model} setModel={setModel} disabled={pending} availableModels={availableModels}/></div>
      <div className="composer-right"><span className="key-hint">{pending?'Sending…':'↵ to send'}</span><button className="send-btn" type="submit" aria-label="Send message" disabled={pending||!text.trim()}><ArrowUp size={18} strokeWidth={2.7}/></button></div>
    </div>
  </form>;
}

function Sidebar({ conversations, selectedId, loading, onSelect, busy }) {
  const [open,setOpen] = useState(true);
  const [mobileOpen,setMobileOpen] = useState(false);
  const [searchOpen,setSearchOpen] = useState(false);
  const [query,setQuery] = useState('');
  const [account,setAccount] = useState(null);
  useEffect(() => {
    fetch('/api/me/',{credentials:'same-origin'}).then(r=>r.ok?r.json():null)
      .then(data=>{if(data?.authenticated)setAccount(data);}).catch(()=>{});
  },[]);
  useEffect(() => { window.kilatChatOpenSidebar = () => setMobileOpen(true); return () => { delete window.kilatChatOpenSidebar; }; }, []);
  const select = id => { setMobileOpen(false); onSelect(id); };
  async function logout() {
    const response = await fetch('/logout/', {method:'POST',credentials:'same-origin',headers:{'X-CSRFToken':csrfToken()}});
    if(response.ok) window.location.href='/login/';
  }
  const visible = conversations.filter(item=>item.title?.toLowerCase().includes(query.toLowerCase()));
  return <>
    {mobileOpen&&<button className="sidebar-scrim" aria-label="Close navigation" onClick={()=>setMobileOpen(false)}/>}
    <aside className={'sidebar '+(!open?'sidebar-collapsed ':'')+(mobileOpen?'sidebar-mobile-open':'')}>
      <div className="sidebar-top"><a className="brand" href="/"><span className="brand-mark"><Zap size={19} fill="currentColor"/></span>{open&&<span className="brand-name">kilat<span>chat</span><span className="brand-dot">.</span></span>}</a><button className="icon-btn collapse-btn" aria-label="Toggle sidebar" onClick={()=>setOpen(!open)}>{open?<PanelLeftClose size={19}/>:<PanelLeftOpen size={19}/>}</button><button className="icon-btn mobile-close" aria-label="Close sidebar" onClick={()=>setMobileOpen(false)}><X size={19}/></button></div>
      <div className="sidebar-actions"><button type="button" className="sidebar-new" disabled={busy} onClick={()=>select(null)}><Plus size={18}/>{open&&<span>New chat</span>}</button>
        <button type="button" className="sidebar-search" onClick={()=>{setOpen(true);setSearchOpen(!searchOpen);}}><Search size={18}/>{open&&<span>Search conversations</span>}</button></div>
      {searchOpen&&open&&<input className="history-search" autoFocus placeholder="Search chat titles..." value={query} onChange={e=>setQuery(e.target.value)}/>}
      {open&&<div className="sidebar-history"><div className="history-label">CONVERSATIONS <MoreHorizontal size={17}/></div>
        {visible.map(c=><button type="button" disabled={busy} key={c.id} onClick={()=>select(c.id)} className={'history-item '+(String(selectedId)===String(c.id)?'history-active':'')} aria-current={String(selectedId)===String(c.id)?'page':undefined}><MessageSquare size={16}/><span>{c.title}</span></button>)}
        {!visible.length&&<div className="history-empty">{loading?'Loading conversations…':query?'No matching conversations':'No conversations yet. Start a new chat.'}</div>}
      </div>}
      <div className="sidebar-bottom"><div className="sidebar-divider"/><a className="sidebar-help" href="/"><CircleHelp size={18}/>{open&&<span>About KilatChat</span>}</a>
        <a className="user-profile" href={account?undefined:'/login/'}><span className="profile-avatar">{account?.username?.[0]?.toUpperCase()||'G'}</span>{open&&<span className="profile-info"><strong>{account?.username||'Guest workspace'}</strong><small>{account?.email||'Not signed in'}</small></span>}</a>
        {account&&<button className="sidebar-help" onClick={logout}><ArrowRight size={18}/>{open&&<span>Log out</span>}</button>}
      </div>
    </aside>
  </>;
}

function InlineText({text}) {
  return <ReactMarkdown remarkPlugins={[remarkGfm]} skipHtml components={{
    a: ({href,children}) => <a href={href} target="_blank" rel="noopener noreferrer">{children}</a>,
  }}>{text}</ReactMarkdown>;
}

export default function Chat() {
  const [activeId,setActiveId] = useState(idFromUrl);
  const [conversations,setConversations] = useState([]);
  const [historyLoading,setHistoryLoading] = useState(true);
  const [threadLoading,setThreadLoading] = useState(false);
  const [messages,setMessages] = useState([]);
  const [draft,setDraft] = useState('');
  const [model,setModel] = useState(DEFAULT_MODEL);
  const [availableModels,setAvailableModels] = useState(fallbackModels);
  const [pending,setPending] = useState(false);
  const [streamingText,setStreamingText] = useState('');
  const [requestSent,setRequestSent] = useState('');
  const [error,setError] = useState('');
  const skipLoad = useRef(false);
  const requestIdRef = useRef(null);
  const requestPayloadRef = useRef(null);
  const bottomRef = useRef(null);
  const currentTitle = conversations.find(c=>String(c.id)===String(activeId))?.title;
  const modelLabel = id => availableModels.find(m=>m.id===id)?.name || id;

  useEffect(()=>{
    fetchConversations().then(setConversations).catch(()=>{}).finally(()=>setHistoryLoading(false));
    fetchModels().then(items=>{
      setAvailableModels(items);
      if(items.length && !items.some(m=>m.id===model))setModel(items[0].id);
    }).catch(()=>{});
    const pop = () => setActiveId(idFromUrl());
    window.addEventListener('popstate', pop);
    return () => window.removeEventListener('popstate',pop);
  },[]);
  useEffect(()=>{
    if(skipLoad.current){skipLoad.current=false;return;}
    if(!activeId){setMessages([]);setError('');setThreadLoading(false);return;}
    let valid=true;
    setMessages([]);setError('');setThreadLoading(true);
    fetchConversation(activeId).then(data=>{
      if(!valid)return;
      setMessages(data.messages.filter(m=>(m.role==='user'||m.role==='assistant')&&typeof m.text==='string'));
      if(data.model)setModel(data.model);
    }).catch(e=>{if(valid)setError(e.message);}).finally(()=>{if(valid)setThreadLoading(false);});
    return ()=>{valid=false;};
  },[activeId]);
  useEffect(()=>{bottomRef.current?.scrollIntoView({behavior:'smooth'});},[messages,pending]);
  function navigate(id){
    if(pending)return;
    window.history.pushState({},'',id?`${CHAT_URL}?conversation=${encodeURIComponent(id)}`:CHAT_URL);
    setActiveId(id);setError('');
    setDraft('');
    requestIdRef.current=null;
    requestPayloadRef.current=null;
    if(!id){setMessages([]);setModel(DEFAULT_MODEL);}
  }
  async function send(message){
    if(pending||threadLoading)return false;
    setPending(true);setError('');setStreamingText('');setRequestSent(message);setDraft('');
    const payloadKey=JSON.stringify([activeId,model,message]);
    if(!requestIdRef.current || requestPayloadRef.current!==payloadKey){
      requestIdRef.current=crypto.randomUUID();
      requestPayloadRef.current=payloadKey;
    }
    let liveReply = '';
    let persistedMeta=null;
    try{
      const result=await sendChatMessage({
        message, model, conversationId:activeId, requestId:requestIdRef.current,
        onMeta: data => {
          if(data.conversation_id != null)persistedMeta=data;
        },
        onDelta: chunk => {
          liveReply += chunk;
          setStreamingText(liveReply);
        },
      });
      setMessages(previous=>[...previous,{role:'user',text:message,model},{role:'assistant',text:result.reply,model}]);
      if(!activeId){
        window.history.replaceState({},'',`${CHAT_URL}?conversation=${encodeURIComponent(result.conversation_id)}`);
        skipLoad.current=true;
        setActiveId(result.conversation_id);
      }
      setConversations(previous=>{
        const id=String(result.conversation_id);
        const previousTitle=previous.find(c=>String(c.id)===id)?.title;
        return [{id:result.conversation_id,title:result.title||previousTitle||message.slice(0,48)},...previous.filter(c=>String(c.id)!==id)];
      });
      setRequestSent('');setStreamingText('');
      requestIdRef.current=null;
      requestPayloadRef.current=null;
      return true;
    }catch(e){
      // A saved prompt must not be sent again automatically if streaming fails.
      if(persistedMeta){
        setMessages(previous=>[...previous,{role:'user',text:message,model,status:'failed'}]);
        if(!activeId){
          window.history.replaceState({},'',`${CHAT_URL}?conversation=${encodeURIComponent(persistedMeta.conversation_id)}`);
          skipLoad.current=true;
          setActiveId(persistedMeta.conversation_id);
        }
        setConversations(previous=>[
          {id:persistedMeta.conversation_id,title:persistedMeta.title||message.slice(0,30)},
          ...previous.filter(c=>String(c.id)!==String(persistedMeta.conversation_id)),
        ]);
        setDraft('');
        requestIdRef.current=null;
        requestPayloadRef.current=null;
      }else{
        // No metadata reached the browser, so preserve the draft for a safe
        // idempotent retry (same request_id if the text and model are unchanged).
        setDraft(message);
      }
      setRequestSent('');setStreamingText('');
      setError(e.message);return false;
    }finally{setPending(false);}
  }
  const hasThread=Boolean(activeId||messages.length||requestSent);
  return <div className="chat-layout">
    <Sidebar conversations={conversations} selectedId={activeId} loading={historyLoading} busy={pending} onSelect={navigate}/>
    <main className="chat-main">
      <header className="chat-header"><div className="chat-header-left"><button className="icon-btn mobile-toggle" aria-label="Open sidebar" onClick={()=>window.kilatChatOpenSidebar?.()}><Menu size={20}/></button><span className="chat-header-title">KilatChat <ChevronDown size={15}/></span>{hasThread&&<span className="header-conversation-label">/ {currentTitle||'Conversation'}</span>}</div><div className="chat-header-right"><span className="preview-indicator"><span className="live-dot"/> Chat</span></div></header>
      {!hasThread?<div className="newchat-center"><div className="newchat-intro"><span className="newchat-symbol"><Zap size={28} fill="currentColor"/></span><div className="newchat-eyebrow">A BLANK PAGE. ENDLESS POSSIBILITY.</div><h1>What’s on your <span>mind?</span></h1><p>From quick questions to big ideas. Start wherever you like.</p></div>
        <div className="newchat-workspace"><Composer model={model} setModel={setModel} onSend={send} pending={pending} text={draft} setText={setDraft} availableModels={availableModels}/>
          {error&&<div className="demo-note chat-error" role="alert"><CircleHelp size={17}/>{error}</div>}
          <div className="suggestions">{starters.map(s=><button key={s.title} disabled={pending} onClick={()=>send(s.prompt)}><span className="suggestion-icon"><s.icon size={19}/></span><span><strong>{s.title}</strong><small>{s.description}</small></span><ArrowUp className="suggestion-arrow" size={15}/></button>)}</div>
        </div></div>:
        <div className="conversation-layout"><div className="conversation-scroll"><div className="conversation-content"><div className="conversation-heading"><div className="conversation-heading-icon"><Sparkles size={18}/></div><span>YOUR CONVERSATION</span></div>
          {threadLoading&&<div className="chat-waiting" role="status">Loading conversation…</div>}
          {messages.map((m,i)=><div key={i} className={'message-row '+m.role}><div className={'message-avatar '+m.role}>{m.role==='user'?'Y':<Zap size={16} fill="currentColor"/>}</div><div className="message-content"><div className="message-role">{m.role==='user'?'You':modelLabel(m.model||model)}{m.status==='failed'?' · Failed':''}</div><div className="message-text"><InlineText text={m.text}/></div>{m.role==='assistant'&&<div className="message-actions"><button title="Copy response" onClick={()=>navigator.clipboard?.writeText(m.text)}><Copy size={15}/></button></div>}</div></div>)}
          {requestSent&&<div className="message-row user"><div className="message-avatar user">Y</div><div className="message-content"><div className="message-role">You</div><div className="message-text"><InlineText text={requestSent}/></div></div></div>}
          {pending&&<div className="message-row assistant"><div className="message-avatar assistant"><Zap size={16} fill="currentColor"/></div><div className="message-content"><div className="message-role">{modelLabel(model)}</div><div className="message-text streaming-markdown" aria-live="polite">{streamingText?<InlineText text={streamingText}/>:<span className="chat-waiting">Thinking…</span>}<span className="stream-cursor" aria-hidden="true"/></div></div></div>}
          {error&&<div className="demo-note chat-error" role="alert"><CircleHelp size={17}/>{error}</div>}<div ref={bottomRef}/></div></div>
          <div className="conversation-bottom"><Composer model={model} setModel={setModel} onSend={send} pending={pending||threadLoading} text={draft} setText={setDraft} availableModels={availableModels}/></div>
        </div>}
      <div className="chat-bottom-caption">Responses are generated by the AI provider through your KilatChat backend.</div>
    </main>
  </div>;
}
