import React, { useEffect, useRef, useState } from 'react';
import { createRoot } from 'react-dom/client';
import {
  ArrowDown, ArrowLeft, ArrowRight, ArrowUp, AudioLines, BookOpen, BrainCircuit,
  Check, ChevronDown, ChevronLeft, ChevronRight, CircleHelp, Code2, Command,
  Compass, Copy, FileText, Globe2, Lightbulb, LockKeyhole, Menu, MessageCircle,
  MessageSquare, MoreHorizontal, PanelLeftClose, PanelLeftOpen, Paperclip,
  Plus, Search, ShieldCheck, Sparkles, WandSparkles, X, Zap
} from 'lucide-react';
import './style.css';
import Chat from './Chat';

const ROUTES = {
  landing: '/', login: '/login/', signup: '/signup/',
  newChat: '/chat/',
};
function csrfToken() {
  return decodeURIComponent(document.cookie.split('; ').find(x => x.startsWith('csrftoken='))?.split('=')[1] || '');
}
const models = [
  { name: 'GPT-6', company: 'OpenAI', color: '#6547d2' },
  { name: 'Claude', company: 'Anthropic', color: '#bd7864' },
  { name: 'Gemini', company: 'Google', color: '#4879d2' },
];
const suggestions = [
  { icon: Lightbulb, title: 'Think something through', description: 'Explore an idea from every angle', prompt: 'Help me think through a new idea.' },
  { icon: Code2, title: 'Build something', description: 'From a snippet to a full project', prompt: 'Help me build a simple web app.' },
  { icon: BookOpen, title: 'Learn a new concept', description: 'Understand something, step by step', prompt: 'Explain how neural networks learn.' },
  { icon: FileText, title: 'Write with clarity', description: 'Find just the right words', prompt: 'Help me outline a research paper.' },
];

function Brand({ inverted = false, compact = false }) {
  return <a className={'brand ' + (inverted ? 'brand-inverted' : '')} href={ROUTES.landing} aria-label="KilatChat home">
    <span className="brand-mark"><Zap size={19} strokeWidth={2.7} fill="currentColor" /></span>
    {!compact && <span className="brand-name">kilat<span>chat</span><span className="brand-dot">.</span></span>}
  </a>;
}

function LinkButton({ href, children, secondary = false, className = '' }) {
  return <a className={'btn ' + (secondary ? 'btn-outline' : 'btn-primary') + ' ' + className} href={href}>{children}</a>;
}

function Landing() {
  return <div className="landing">
    <div className="landing-glow" />
    <header className="site-header wrap">
      <Brand inverted />
      <nav className="site-nav"><a href="#features">Features</a><a href="#how-it-works">How it works</a><a href="#about">About</a></nav>
      <div className="site-actions"><a className="header-login" href={ROUTES.login}>Log in</a><LinkButton href={ROUTES.signup}>Get started <ArrowRight size={16}/></LinkButton></div>
    </header>

    <main>
      <section className="hero wrap">
        <div className="hero-copy">
          <div className="eyebrow"><span className="live-dot"/> YOUR THINKING SPACE, REIMAGINED <ArrowRight size={13}/></div>
          <h1>Big ideas.<br/><span className="hero-accent">Better conversations.</span></h1>
          <p>One beautiful space to think, create, and explore with AI. Less switching tabs. More of those <em>aha</em> moments.</p>
          <div className="hero-buttons"><LinkButton href={ROUTES.signup}>Start chatting for free <ArrowRight size={18}/></LinkButton><LinkButton secondary href={ROUTES.newChat}>Explore the interface <ArrowRight size={17}/></LinkButton></div>
          <div className="hero-footnote"><span className="avatars"><span>A</span><span>M</span><span>J</span></span><span>Your next great idea starts here.</span></div>
        </div>
        <div className="hero-visual">
          <div className="visual-orbit visual-orbit-one"/>
          <div className="visual-orbit visual-orbit-two"/>
          <div className="sparkle-floating sparkle-one"><Sparkles size={20}/></div>
          <div className="sparkle-floating sparkle-two"><Zap size={17} fill="currentColor"/></div>
          <div className="preview-window">
            <div className="preview-top"><div className="window-dots"><i/><i/><i/></div><span>KilatChat / Workspace</span><MoreHorizontal size={16}/></div>
            <div className="preview-body">
              <div className="preview-label"><span className="preview-icon"><Zap size={14} fill="currentColor"/></span> KilatChat <span className="preview-model">GPT-6 <ChevronDown size={12}/></span></div>
              <div className="preview-greeting">Where should we <span>begin?</span></div>
              <div className="preview-input">Ask anything, imagine everything... <span><ArrowUp size={16}/></span></div>
              <div className="preview-tags"><span><Lightbulb size={13}/> Brainstorm</span><span><Code2 size={13}/> Code</span><span><BookOpen size={13}/> Learn</span></div>
              <div className="preview-message"><span className="small-avatar">Y</span><span>Help me turn an idea into something real.</span></div>
              <div className="preview-reply"><span className="preview-icon"><Zap size={13} fill="currentColor"/></span><div>Absolutely. Every great thing starts with a curious question. <span className="skeleton-line"/><span className="skeleton-line short"/></div></div>
            </div>
          </div>
          <div className="float-chip"><span className="chip-icon"><Sparkles size={16}/></span><span>Curiosity looks good on you <small>Keep exploring ✦</small></span></div>
        </div>
      </section>
      <section className="trust-band"><div className="wrap trust-content"><span>MORE ROOM FOR WHAT MATTERS</span><div><Sparkles size={16}/> Think freely</div><div><BrainCircuit size={17}/> Explore deeply</div><div><Zap size={17}/> Create boldly</div></div></section>
      <section className="features wrap" id="features">
        <div className="section-intro"><div className="section-kicker">MADE FOR YOUR MIND</div><h2>Everything clicks<br/>when ideas <span>connect.</span></h2><p>One thoughtfully designed workspace for your everyday curiosity and ambitious projects.</p></div>
        <div className="feature-grid">
          <article className="feature-card feature-purple"><span className="feature-icon"><MessageCircle size={23}/></span><h3>Conversations that flow.</h3><p>Pick up a thought, take it further, and keep the good ideas coming.</p><div className="feature-art art-chat"><span>What if we tried a different approach?</span><span>That's an interesting direction. Let's explore it.</span></div></article>
          <article className="feature-card feature-peach"><span className="feature-icon"><Compass size={23}/></span><h3>Your curiosity, unlimited.</h3><p>From the smallest question to your biggest what-if. Start anywhere.</p><div className="feature-art art-explore"><span><Lightbulb/> Imagine</span><span><Code2/> Build</span><span><BookOpen/> Learn</span></div></article>
          <article className="feature-card feature-lilac"><span className="feature-icon"><WandSparkles size={23}/></span><h3>One space. Many possibilities.</h3><p>A calm, organized home for everything you're working through.</p><div className="feature-art art-stack"><div>Research paper ideas <ArrowRight size={14}/></div><div>Next big project <ArrowRight size={14}/></div></div></article>
        </div>
      </section>
      <section className="cta-block wrap" id="how-it-works"><div className="cta-inner"><span className="section-kicker">READY WHEN YOU ARE</span><h2>Your next idea is<br/>one conversation away.</h2><p>Make some room for the extraordinary.</p><LinkButton href={ROUTES.signup}>Get started for free <ArrowRight size={18}/></LinkButton><div className="cta-star one">✳</div><div className="cta-star two">✳</div></div></section>
    </main>
    <footer className="footer wrap" id="about"><Brand/><span>© {new Date().getFullYear()} KilatChat. Built for the curious.</span><div><a href={ROUTES.login}>Log in</a><a href={ROUTES.signup}>Get started</a></div></footer>
  </div>;
}

function Auth({ mode }) {
  const isSignup = mode === 'signup';
  const [visible, setVisible] = useState(false);
  const [values, setValues] = useState({ username: '', email: '', password: '' });
  const [note, setNote] = useState('');
  async function submit(e) {
    e.preventDefault();
    setNote('');
    try {
      const response = await fetch(isSignup ? ROUTES.signup : ROUTES.login, {
        method: 'POST',
        credentials: 'same-origin',
        headers: { 'X-CSRFToken': csrfToken() },
        body: new URLSearchParams(isSignup ? values : { email: values.email, password: values.password }),
      });
      const result = await response.json();
      if (response.ok && result.ok) {
        window.location.assign(result.redirect || ROUTES.newChat);
        return;
      }
      const firstError = Object.values(result.errors || {}).flat()[0];
      setNote(firstError?.message || result.error || 'Please check your details and try again.');
    } catch {
      setNote('Unable to reach the server. Please try again.');
    }
  }
  return <div className="auth-layout">
    <section className="auth-panel">
      <header><Brand/><a href={ROUTES.landing} className="back-link"><ArrowLeft size={15}/> Back to home</a></header>
      <div className="auth-main">
        <div className="auth-top-icon"><Zap size={21} fill="currentColor"/></div>
        <div className="auth-kicker">YOUR SPACE AWAITS</div>
        <h1>{isSignup ? 'Let’s get curious.' : 'Welcome back.'}</h1>
        <p className="auth-subtitle">{isSignup ? 'A universe of ideas is one step away. Create your space to get started.' : 'Good to see you again. Your ideas are right where you left them.'}</p>
        <form className="auth-form" onSubmit={submit}>
          {isSignup && <label>Username<input type="text" required maxLength={30} autoComplete="username" placeholder="Your username" value={values.username} onChange={e => setValues({...values,username:e.target.value})}/></label>}
          <label>Email address<input type="email" required autoComplete="email" placeholder="you@example.com" value={values.email} onChange={e => setValues({...values,email:e.target.value})}/></label>
          <label>{isSignup ? 'Create a password' : 'Password'}<div className="password-field"><input required type={visible?'text':'password'} minLength={8} autoComplete={isSignup?'new-password':'current-password'} placeholder="At least 8 characters" value={values.password} onChange={e => setValues({...values,password:e.target.value})}/><button type="button" aria-label={visible?'Hide password':'Show password'} onClick={()=>setVisible(!visible)}>{visible ? 'Hide' : 'Show'}</button></div></label>
          {!isSignup && <div className="forgot-note">Forgot password? <span>Coming soon</span></div>}
          <button className="btn btn-primary auth-submit" type="submit">{isSignup ? 'Create account' : 'Log in'} <ArrowRight size={18}/></button>
          {note && <div className="auth-notice" role="status"><CircleHelp size={17}/>{note}</div>}
        </form>
        <div className="auth-switch">{isSignup ? 'Already have an account?' : 'New to KilatChat?'} <a href={isSignup ? ROUTES.login : ROUTES.signup}>{isSignup ? 'Log in' : 'Create an account'} <ArrowRight size={14}/></a></div>
        <p className="auth-small"><LockKeyhole size={14}/> A calm place for big thoughts.</p>
      </div>
      <div className="auth-footer">© {new Date().getFullYear()} KilatChat</div>
    </section>
    <section className="auth-art"><div className="auth-art-grid"/><div className="auth-art-content"><div className="auth-orb"><div className="auth-orb-core"><Zap size={70} fill="currentColor" strokeWidth={1.7}/></div><span className="orb-spark one">✳</span><span className="orb-spark two">✦</span><span className="orb-spark three">✳</span></div><div className="auth-quote">“The best ideas start<br/>with <em>one question.</em>”</div><p>Where curiosity meets possibility.</p></div><div className="auth-art-bottom"><span className="live-dot"/> A little spark goes a long way <Sparkles size={16}/></div></section>
  </div>;
}

const currentPage = document.getElementById('root')?.dataset.page || 'landing';
const screens = {
  'landing': <Landing/>,
  'login': <Auth mode="login"/>,
  'signup': <Auth mode="signup"/>,
  'new-chat': <Chat/>,
  'conversation': <Chat/>,
};
createRoot(document.getElementById('root')).render(screens[currentPage] || <Landing/>);
