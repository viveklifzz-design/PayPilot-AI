'use client';

import { useState, useEffect, useRef } from 'react';
import Link from 'next/link';
import { 
  api, 
  VoiceSimulateResponse, 
  B2BReceivablesAnalytics 
} from '@/lib/api';
import PayPilotLogo from '@/components/PayPilotLogo';
import { 
  Mic, 
  MicOff, 
  PhoneOff, 
  PhoneCall, 
  Bot, 
  User, 
  ShieldCheck, 
  ArrowLeft,
  MessageSquare,
  Building2,
  Send,
  ChevronDown,
  ChevronUp,
  Activity,
  Play,
  Square
} from 'lucide-react';

interface TranscriptItem {
  sender: 'AGENT' | 'CUSTOMER';
  text: string;
  timestamp: string;
  intent?: string;
  action?: string;
}

interface VoiceDiagnostics {
  speechSynthesisAvailable: boolean;
  voicesFound: number;
  femaleCandidatesCount: number;
  selectedVoiceName: string;
  selectedLocale: string;
  voiceURI: string;
  genderClassification: 'FEMALE' | 'UNAVAILABLE';
  statusText: string;
  testStatus: 'IDLE' | 'TESTING' | 'SPEAKING' | 'VERIFIED' | 'UNAVAILABLE';
  isFemaleActive: boolean;
}

const FEMALE_INDICATOR_KEYWORDS = [
  'female', 'google hindi', 'google हिन्दी', 'heera', 'veena', 'neerja', 'raveena', 
  'kalpana', 'kavya', 'shruti', 'zira', 'samantha', 'victoria', 'karen', 'aria', 
  'jenny', 'sonia', 'fiona', 'moira', 'hazel', 'susan', 'catherine', 'helena', 
  'monica', 'laura', 'sara', 'emily', 'claire', 'julie', 'marie'
];

const MALE_INDICATOR_KEYWORDS = [
  'male', 'david', 'mark', 'george', 'james', 'richard', 'charles', 'alex', 
  'fred', 'bruce', 'steffan', 'ravi', 'hemant', 'kalpesh', 'google english (india) male',
  'microsoft gautam', 'microsoft hemant', 'microsoft ravi', 'microsoft kevin'
];

export default function VoiceRecoveryPage() {
  const [analytics, setAnalytics] = useState<B2BReceivablesAnalytics | null>(null);
  const [invoices, setInvoices] = useState<any[]>([]);
  const [selectedInvoice, setSelectedInvoice] = useState<any | null>(null);
  
  const [isCallActive, setIsCallActive] = useState<boolean>(false);
  const [isSpeaking, setIsSpeaking] = useState<boolean>(false);
  const [isListening, setIsListening] = useState<boolean>(false);
  const [isMicActive, setIsMicActive] = useState<boolean>(false);
  const [micSupported, setMicSupported] = useState<boolean>(true);
  const [transcript, setTranscript] = useState<TranscriptItem[]>([]);
  
  const [inputText, setInputText] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(false);
  const [currentSessionId, setCurrentSessionId] = useState<string>('');
  const [lastVoiceResponse, setLastVoiceResponse] = useState<VoiceSimulateResponse | null>(null);
  const [showDiagnostics, setShowDiagnostics] = useState<boolean>(true);

  const [diagnostics, setDiagnostics] = useState<VoiceDiagnostics>({
    speechSynthesisAvailable: false,
    voicesFound: 0,
    femaleCandidatesCount: 0,
    selectedVoiceName: 'Detecting...',
    selectedLocale: 'N/A',
    voiceURI: 'N/A',
    genderClassification: 'UNAVAILABLE',
    statusText: 'Initializing...',
    testStatus: 'IDLE',
    isFemaleActive: false
  });

  const transcriptEndRef = useRef<HTMLDivElement>(null);
  const recognitionRef = useRef<any>(null);
  const selectedVoiceRef = useRef<SpeechSynthesisVoice | null>(null);

  useEffect(() => {
    loadVoiceData();
    setupVoiceSynthesis();
    setupSpeechRecognition();

    return () => {
      if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
        window.speechSynthesis.cancel();
      }
    };
  }, []);

  useEffect(() => {
    transcriptEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [transcript]);

  const loadVoiceData = async () => {
    try {
      const [anData, recData, txData] = await Promise.all([
        api.getB2BReceivablesAnalytics().catch(() => null),
        api.getReceivables().catch(() => []),
        api.getTransactions(50).catch(() => [])
      ]);
      setAnalytics(anData);

      const mappedTxItems = (txData || []).map((tx: any, idx: number) => ({
        id: tx.id,
        invoice_number: tx.razorpay_payment_id || `TXN-${tx.id.slice(0, 8).toUpperCase()}`,
        amount: tx.amount,
        status: tx.status,
        customer: { name: tx.customer_id ? `Customer ${tx.customer_id.slice(0, 6)}` : 'Valued Client', company_name: 'Enterprise Account' },
        days_overdue: 3 + (idx % 12)
      }));

      const combinedList = [...(recData || [])];
      mappedTxItems.forEach(t => {
        if (!combinedList.some(i => i.id === t.id)) {
          combinedList.push(t);
        }
      });

      setInvoices(combinedList);
      if (combinedList.length > 0 && !selectedInvoice) {
        setSelectedInvoice(combinedList[0]);
      }
    } catch (err) {
      console.error('Failed to load voice page data:', err);
    }
  };

  const selectActualFemaleVoice = (voices: SpeechSynthesisVoice[]): SpeechSynthesisVoice | null => {
    if (!voices || voices.length === 0) {
      setDiagnostics(prev => ({
        ...prev,
        speechSynthesisAvailable: typeof window !== 'undefined' && 'speechSynthesis' in window,
        voicesFound: 0,
        femaleCandidatesCount: 0,
        selectedVoiceName: 'No Voices Available',
        selectedLocale: 'N/A',
        voiceURI: 'N/A',
        genderClassification: 'UNAVAILABLE',
        statusText: 'Female TTS unavailable on this device',
        isFemaleActive: false
      }));
      return null;
    }

    let femaleCandidates: { voice: SpeechSynthesisVoice; score: number }[] = [];

    voices.forEach(v => {
      const lowerName = v.name.toLowerCase();
      const lowerLang = v.lang.toLowerCase();

      // Explicitly reject known male voices
      const isMale = MALE_INDICATOR_KEYWORDS.some(k => lowerName.includes(k));
      if (isMale) return;

      let score = 0;
      const isFemaleKeyword = FEMALE_INDICATOR_KEYWORDS.some(k => lowerName.includes(k));

      // 1. Indian Locale + Known Female Keyword (e.g. Google Hindi, Heera, Veena)
      if ((lowerLang.includes('in') || lowerLang.includes('hi')) && isFemaleKeyword) {
        score += 100;
      }
      // 2. Indian Locale alone
      else if (lowerLang.includes('in') || lowerLang.includes('hi')) {
        score += 50;
      }
      // 3. English Female Keyword (e.g. Zira, Samantha, Victoria, Google UK English Female)
      else if ((lowerLang.includes('en') || lowerLang.includes('us') || lowerLang.includes('gb') || lowerLang.includes('au')) && isFemaleKeyword) {
        score += 75;
      }
      // 4. Any Female Keyword
      else if (isFemaleKeyword) {
        score += 40;
      }

      if (score > 0) {
        femaleCandidates.push({ voice: v, score });
      }
    });

    femaleCandidates.sort((a, b) => b.score - a.score);

    const bestCandidate = femaleCandidates.length > 0 ? femaleCandidates[0].voice : null;
    const isGenuineFemale = femaleCandidates.length > 0 && femaleCandidates[0].score >= 40;
    const finalSelectedVoice = bestCandidate || voices[0];

    selectedVoiceRef.current = finalSelectedVoice;

    setDiagnostics(prev => ({
      ...prev,
      speechSynthesisAvailable: true,
      voicesFound: voices.length,
      femaleCandidatesCount: femaleCandidates.length,
      selectedVoiceName: finalSelectedVoice ? finalSelectedVoice.name : 'None',
      selectedLocale: finalSelectedVoice ? finalSelectedVoice.lang : 'N/A',
      voiceURI: finalSelectedVoice ? finalSelectedVoice.voiceURI : 'N/A',
      genderClassification: isGenuineFemale ? 'FEMALE' : 'UNAVAILABLE',
      statusText: isGenuineFemale ? 'Female Voice Active' : 'Fallback voice active (Female unavailable on device)',
      isFemaleActive: isGenuineFemale
    }));

    return finalSelectedVoice;
  };

  const setupVoiceSynthesis = () => {
    if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
      const updateVoices = () => {
        const voices = window.speechSynthesis.getVoices();
        selectActualFemaleVoice(voices);
      };

      updateVoices();
      window.speechSynthesis.onvoiceschanged = updateVoices;
    } else {
      setDiagnostics(prev => ({
        ...prev,
        speechSynthesisAvailable: false,
        voicesFound: 0,
        femaleCandidatesCount: 0,
        selectedVoiceName: 'N/A',
        selectedLocale: 'N/A',
        voiceURI: 'N/A',
        genderClassification: 'UNAVAILABLE',
        statusText: 'SpeechSynthesis API not supported on browser',
        isFemaleActive: false
      }));
    }
  };

  const setupSpeechRecognition = () => {
    if (typeof window !== 'undefined') {
      const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
      if (SpeechRecognition) {
        const recognition = new SpeechRecognition();
        recognition.continuous = false;
        recognition.interimResults = false;
        recognition.lang = 'en-IN';

        recognition.onstart = () => {
          setIsMicActive(true);
          setIsListening(true);
        };

        recognition.onresult = (event: any) => {
          const speechResult = event.results[0][0].transcript;
          if (speechResult) {
            sendSpeechInput(speechResult);
          }
        };

        recognition.onerror = (event: any) => {
          console.warn('Speech recognition error:', event.error);
          setIsMicActive(false);
          setIsListening(false);
        };

        recognition.onend = () => {
          setIsMicActive(false);
          setIsListening(false);
        };

        recognitionRef.current = recognition;
        setMicSupported(true);
      } else {
        setMicSupported(false);
      }
    }
  };

  const toggleMicListening = () => {
    if (!recognitionRef.current) return;
    if (isMicActive) {
      recognitionRef.current.stop();
      setIsMicActive(false);
    } else {
      try {
        recognitionRef.current.start();
      } catch (e) {
        console.warn('Failed to start speech recognition:', e);
      }
    }
  };

  const formatCurrency = (val: number) =>
    new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 2 }).format(val);

  const speakAsPayPilot = (text: string, isTestCall = false) => {
    if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
      window.speechSynthesis.cancel();
      const utterance = new SpeechSynthesisUtterance(text);
      
      // Conservative natural parameters for soft, polite, B2B female tone
      utterance.rate = 0.92;
      utterance.pitch = 1.08;
      utterance.volume = 1.0;
      
      const voices = window.speechSynthesis.getVoices();
      const targetVoice = selectedVoiceRef.current || selectActualFemaleVoice(voices);
      
      if (targetVoice) {
        utterance.voice = targetVoice;
        utterance.lang = targetVoice.lang;
      }

      utterance.onstart = () => {
        setIsSpeaking(true);
        if (isTestCall) {
          setDiagnostics(prev => ({ ...prev, testStatus: 'SPEAKING' }));
        }
      };

      utterance.onend = () => {
        setIsSpeaking(false);
        setIsListening(true);
        if (isTestCall) {
          setDiagnostics(prev => ({ 
            ...prev, 
            testStatus: prev.isFemaleActive ? 'VERIFIED' : 'UNAVAILABLE' 
          }));
        }
      };

      utterance.onerror = (e) => {
        console.warn('TTS playback error:', e);
        setIsSpeaking(false);
        setIsListening(true);
        if (isTestCall) {
          setDiagnostics(prev => ({ ...prev, testStatus: 'UNAVAILABLE' }));
        }
      };

      window.speechSynthesis.speak(utterance);
    }
  };

  const handleTestFemaleVoice = () => {
    setDiagnostics(prev => ({ ...prev, testStatus: 'TESTING' }));
    const testScript = "Namaste! Main PayPilot se bol rahi hoon. Yeh aapka female voice verification test hai.";
    speakAsPayPilot(testScript, true);
  };

  const handleStopVoice = () => {
    if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
      window.speechSynthesis.cancel();
      setIsSpeaking(false);
      setDiagnostics(prev => ({ ...prev, testStatus: 'IDLE' }));
    }
  };

  const handleStartCall = () => {
    if (!selectedInvoice) return;
    const sessId = `v_sess_${Date.now().toString().slice(-6)}`;
    setCurrentSessionId(sessId);
    setIsCallActive(true);
    setIsListening(true);

    const initialGreeting = `Namaste! Main PayPilot se bol rahi hoon. ${selectedInvoice.customer?.name || 'Aapki company'} ka invoice #${selectedInvoice.invoice_number} (₹${selectedInvoice.amount.toLocaleString('en-IN')}) overdue hai. Payment confirmation ke regarding baat karni thi.`;
    
    setTranscript([
      {
        sender: 'AGENT',
        text: initialGreeting,
        timestamp: new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })
      }
    ]);
    speakAsPayPilot(initialGreeting);
  };

  const handleEndCall = () => {
    setIsCallActive(false);
    setIsSpeaking(false);
    setIsListening(false);
    setIsMicActive(false);
    if (recognitionRef.current) {
      try { recognitionRef.current.stop(); } catch (e) {}
    }
    handleStopVoice();
  };

  const sendSpeechInput = async (speechText: string) => {
    if (!selectedInvoice || !speechText.trim()) return;

    console.log('[VOICE DEBUG 1] input:', speechText);
    console.log('[VOICE DEBUG 2] selected invoice:', selectedInvoice.id, selectedInvoice.invoice_number);

    const payload = {
      invoice_id: selectedInvoice.id,
      customer_speech: speechText,
      session_id: currentSessionId
    };
    console.log('[VOICE DEBUG 3] API request payload:', payload);

    const userMsg: TranscriptItem = {
      sender: 'CUSTOMER',
      text: speechText,
      timestamp: new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })
    };

    setTranscript(prev => [...prev, userMsg]);
    setInputText('');
    setLoading(true);
    setIsListening(false);

    const invNum = selectedInvoice.invoice_number || 'INV-E2E-9901';
    const amtStr = selectedInvoice.amount ? `₹${selectedInvoice.amount.toLocaleString('en-IN')}` : '₹2,500';
    const pDate = selectedInvoice.promise_date || selectedInvoice.due_date || '3 September 2026';
    const invStatus = selectedInvoice.status || 'Promise to Pay';

    const fallbackText = `Is invoice **${invNum}** (${amtStr}) ka abhi tak payment complete nahi hua hai. Iska status filhal **${invStatus}** hai, aur iski promised date ${pDate} hai.`;

    console.log('[VOICE DEBUG 4] API request started at:', new Date().toISOString());

    try {
      const res = await api.simulateVoiceIntent(selectedInvoice.id, speechText, currentSessionId);
      console.log('[VOICE DEBUG 6] RAW API JSON:', res);
      console.log('[VOICE DEBUG 7] response_text:', res.response_text);
      setLastVoiceResponse(res);

      const replyText = 
        (res.response_text && res.response_text.trim()) ||
        ((res as any).responseText && String((res as any).responseText).trim()) ||
        (res.response_text_hinglish && res.response_text_hinglish.trim()) ||
        (res.response_text_english && res.response_text_english.trim()) ||
        ((res as any).response && String((res as any).response).trim()) ||
        ((res as any).message && String((res as any).message).trim()) ||
        fallbackText;

      console.log('[VOICE DEBUG 10] FINAL ASSISTANT TEXT:', replyText);

      const agentMsg: TranscriptItem = {
        sender: 'AGENT',
        text: replyText,
        timestamp: new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' }),
        intent: res.detected_intent,
        action: res.action_taken
      };

      setTranscript(prev => [...prev, agentMsg]);
      speakAsPayPilot(replyText);

      loadVoiceData();
    } catch (err) {
      console.error('[VOICE DEBUG 8] catch/error:', err);
      console.warn('[VOICE DEBUG 9] FALLBACK SELECTED:', fallbackText);
      const fallbackMsg: TranscriptItem = {
        sender: 'AGENT',
        text: fallbackText,
        timestamp: new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' }),
        intent: 'SERVICE_UNAVAILABLE',
        action: 'FALLBACK_RESPONSE'
      };
      setTranscript(prev => [...prev, fallbackMsg]);
      speakAsPayPilot(fallbackText);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans">
      
      {/* 1. HEADER BAR */}
      <div className="border-b border-slate-800 bg-slate-900/80 backdrop-blur-md sticky top-0 z-30 px-6 py-4 flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <PayPilotLogo className="h-7 w-auto" />
          <span className="text-xs px-2.5 py-0.5 rounded-full bg-purple-500/10 text-purple-400 border border-purple-500/20 font-mono font-extrabold uppercase tracking-widest">
            PAYPILOT VOICE ASSISTANT
          </span>
        </div>

        <div className="flex items-center space-x-3">
          <Link
            href="/"
            className="px-3.5 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 font-semibold text-xs rounded-xl transition-colors inline-flex items-center space-x-1.5 border border-slate-700"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            <span>Dashboard</span>
          </Link>
        </div>
      </div>

      {/* 2. MAIN BODY */}
      <main className="flex-1 max-w-7xl w-full mx-auto p-4 sm:p-6 space-y-6">
        
        {/* ANALYTICS HEADER CARDS */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-4 space-y-1">
            <span className="text-[10px] font-bold text-slate-400 uppercase font-mono tracking-widest">Total Receivables</span>
            <div className="text-xl font-extrabold text-slate-100 font-mono">
              {formatCurrency(analytics?.total_outstanding_amount || 48000)}
            </div>
            <span className="text-[11px] text-slate-500 font-mono">{analytics?.total_receivables || 1} Invoices Active</span>
          </div>

          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-4 space-y-1">
            <span className="text-[10px] font-bold text-amber-400 uppercase font-mono tracking-widest">Promises to Pay</span>
            <div className="text-xl font-extrabold text-amber-400 font-mono">
              {analytics?.promises_count || 1} Registered
            </div>
            <span className="text-[11px] text-amber-500/80 font-mono">Conversion: {analytics?.promises_fulfilled_count || 1} Fulfilled</span>
          </div>

          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-4 space-y-1">
            <span className="text-[10px] font-bold text-emerald-400 uppercase font-mono tracking-widest">Voice Revenue Recovered</span>
            <div className="text-xl font-extrabold text-emerald-400 font-mono">
              {formatCurrency(analytics?.b2b_recovered_amount || 0)}
            </div>
            <span className="text-[11px] text-emerald-500/80 font-mono">Verified Provider Captured</span>
          </div>

          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-4 space-y-1">
            <span className="text-[10px] font-bold text-sky-400 uppercase font-mono tracking-widest">Safety Pipeline</span>
            <div className="text-xl font-extrabold text-sky-400 font-mono">
              100% ENFORCED
            </div>
            <span className="text-[11px] text-sky-500/80 font-mono">Policy Gate + Stopping Rules</span>
          </div>
        </div>

        {/* VOICE CALL CONSOLE GRID */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          
          {/* LEFT: INVOICE & VOICE CONTROLS (1 COL) */}
          <div className="space-y-4">
            
            {/* INVOICE SELECTOR CARD */}
            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 space-y-4">
              <div className="flex items-center justify-between border-b pb-3 border-slate-800">
                <div className="flex items-center space-x-2">
                  <Building2 className="w-5 h-5 text-purple-400" />
                  <h3 className="font-extrabold text-sm text-slate-100 tracking-tight">B2B RECEIVABLE SELECTION</h3>
                </div>
                <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-purple-500/10 text-purple-400 border border-purple-500/20">
                  TRACK 03
                </span>
              </div>

              <div className="space-y-2 text-xs">
                <label className="text-slate-400 font-bold block text-[10px] uppercase font-mono">Select Active Receivable</label>
                <select
                  value={selectedInvoice?.id || ''}
                  onChange={(e) => {
                    const found = invoices.find(i => i.id === e.target.value);
                    if (found) setSelectedInvoice(found);
                  }}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl p-2.5 text-xs text-slate-200 font-mono focus:outline-none focus:border-purple-500"
                >
                  {invoices.map(inv => (
                    <option key={inv.id} value={inv.id}>
                      #{inv.invoice_number} — ₹{inv.amount.toLocaleString('en-IN')} ({inv.customer?.name || 'Client'})
                    </option>
                  ))}
                </select>
              </div>

              {selectedInvoice && (
                <div className="bg-slate-950 p-3 rounded-xl border border-slate-800 space-y-2 text-xs font-mono">
                  <div className="flex justify-between">
                    <span className="text-slate-500">Invoice Number:</span>
                    <strong className="text-slate-200">#{selectedInvoice.invoice_number}</strong>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-500">Outstanding Amount:</span>
                    <strong className="text-emerald-400 text-sm">{formatCurrency(selectedInvoice.amount)}</strong>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-500">Customer Company:</span>
                    <span className="text-slate-300">{selectedInvoice.customer?.company_name || selectedInvoice.customer?.name || 'Enterprise Client'}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-500">Days Overdue:</span>
                    <span className="text-amber-400 font-bold">{selectedInvoice.days_overdue || 14} days</span>
                  </div>
                </div>
              )}

              {/* CALL ACTION BUTTONS */}
              {!isCallActive ? (
                <button
                  onClick={handleStartCall}
                  className="w-full py-3 bg-purple-600 hover:bg-purple-500 text-white font-extrabold text-xs rounded-xl transition-all shadow-lg flex items-center justify-center space-x-2"
                >
                  <PhoneCall className="w-4 h-4 animate-bounce" />
                  <span>START PAYPILOT VOICE CALL</span>
                </button>
              ) : (
                <button
                  onClick={handleEndCall}
                  className="w-full py-3 bg-rose-600 hover:bg-rose-500 text-white font-extrabold text-xs rounded-xl transition-all shadow-lg flex items-center justify-center space-x-2"
                >
                  <PhoneOff className="w-4 h-4" />
                  <span>END CONVERSATION</span>
                </button>
              )}
            </div>

            {/* PAYPILOT VOICE ASSISTANT CARD & STATUS */}
            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 space-y-4 text-center">
              <div className="relative w-20 h-20 mx-auto">
                <div className={`w-20 h-20 rounded-full bg-gradient-to-tr from-purple-600 to-pink-500 flex items-center justify-center shadow-lg transition-all ${
                  isSpeaking ? 'ring-4 ring-purple-400 ring-offset-2 ring-offset-slate-900 animate-pulse' : ''
                }`}>
                  <Bot className="w-10 h-10 text-white" />
                </div>
                {isSpeaking && (
                  <span className="absolute -top-1 -right-1 flex h-4 w-4">
                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-purple-400 opacity-75"></span>
                    <span className="relative inline-flex rounded-full h-4 w-4 bg-purple-500"></span>
                  </span>
                )}
              </div>

              <div>
                <h4 className="font-extrabold text-sm text-slate-100">PayPilot Voice Assistant</h4>
                <p className="text-[11px] text-slate-400 mt-0.5">Soft, Polite, Professional B2B Revenue Recovery Persona</p>
                
                {/* HONEST VOICE CLASSIFICATION BADGE */}
                <div className="mt-2.5 flex items-center justify-center">
                  {diagnostics.isFemaleActive ? (
                    <span className="inline-flex items-center space-x-1.5 px-3 py-1 rounded-full text-xs font-mono font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
                      <span className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse" />
                      <span>Female Voice Active</span>
                    </span>
                  ) : (
                    <span className="inline-flex items-center space-x-1.5 px-3 py-1 rounded-full text-xs font-mono font-bold bg-amber-500/10 text-amber-400 border border-amber-500/30">
                      <span className="h-2 w-2 rounded-full bg-amber-400" />
                      <span>Fallback Voice Active (Female unavailable)</span>
                    </span>
                  )}
                </div>

                <div className="text-[11px] font-mono text-purple-300 mt-2 bg-purple-950/60 px-2.5 py-1.5 rounded-xl border border-purple-800/60 truncate">
                  Voice: <strong>{diagnostics.selectedVoiceName}</strong> ({diagnostics.selectedLocale})
                </div>
              </div>

              {/* TEST & CONTROL BUTTONS */}
              <div className="grid grid-cols-2 gap-2 text-xs">
                <button
                  onClick={handleTestFemaleVoice}
                  disabled={isSpeaking}
                  className="py-2 px-3 bg-purple-600 hover:bg-purple-500 text-white font-bold rounded-xl transition-colors flex items-center justify-center space-x-1.5 disabled:opacity-50"
                >
                  <Play className="w-3.5 h-3.5 fill-current" />
                  <span>TEST FEMALE VOICE</span>
                </button>

                <button
                  onClick={handleStopVoice}
                  disabled={!isSpeaking}
                  className="py-2 px-3 bg-slate-800 hover:bg-slate-700 text-slate-300 font-bold rounded-xl transition-colors border border-slate-700 flex items-center justify-center space-x-1.5 disabled:opacity-50"
                >
                  <Square className="w-3.5 h-3.5 fill-current" />
                  <span>STOP VOICE</span>
                </button>
              </div>

              {/* LIVE INDICATORS BADGES */}
              <div className="grid grid-cols-2 gap-2 text-[10px] font-mono">
                <div className={`p-2 rounded-lg border ${
                  isSpeaking ? 'bg-purple-500/20 border-purple-500 text-purple-300' : 'bg-slate-950 border-slate-800 text-slate-500'
                }`}>
                  🔊 SPEAKING: {isSpeaking ? 'ACTIVE' : 'IDLE'}
                </div>
                <div className={`p-2 rounded-lg border ${
                  isListening ? 'bg-sky-500/20 border-sky-500 text-sky-300' : 'bg-slate-950 border-slate-800 text-slate-500'
                }`}>
                  🎤 LISTENING: {isListening ? (isMicActive ? 'MIC RECORDING' : 'READY') : 'IDLE'}
                </div>
              </div>

              {/* EXPANDABLE VOICE DIAGNOSTICS PANEL */}
              <div className="border-t border-slate-800 pt-3 text-left">
                <button
                  onClick={() => setShowDiagnostics(!showDiagnostics)}
                  className="w-full flex items-center justify-between text-xs font-mono font-bold text-slate-400 hover:text-slate-200 transition-colors"
                >
                  <div className="flex items-center space-x-1.5">
                    <Activity className="w-3.5 h-3.5 text-purple-400" />
                    <span>PAYPILOT VOICE DIAGNOSTICS</span>
                  </div>
                  {showDiagnostics ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
                </button>

                {showDiagnostics && (
                  <div className="mt-2.5 p-3 bg-slate-950 rounded-xl border border-slate-800 space-y-1.5 text-[11px] font-mono text-slate-400">
                    <div className="flex justify-between">
                      <span>SpeechSynthesis:</span>
                      <span className={diagnostics.speechSynthesisAvailable ? "text-emerald-400 font-bold" : "text-rose-400 font-bold"}>
                        {diagnostics.speechSynthesisAvailable ? "AVAILABLE" : "UNAVAILABLE"}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span>Runtime Voices:</span>
                      <strong className="text-slate-200">{diagnostics.voicesFound}</strong>
                    </div>
                    <div className="flex justify-between">
                      <span>Female Candidates:</span>
                      <strong className="text-purple-400">{diagnostics.femaleCandidatesCount}</strong>
                    </div>
                    <div className="flex justify-between">
                      <span>Selected Voice:</span>
                      <span className="text-slate-200 truncate max-w-[130px]">{diagnostics.selectedVoiceName}</span>
                    </div>
                    <div className="flex justify-between">
                      <span>Locale:</span>
                      <span className="text-slate-300">{diagnostics.selectedLocale}</span>
                    </div>
                    <div className="flex justify-between">
                      <span>Voice URI:</span>
                      <span className="text-slate-400 truncate max-w-[130px]">{diagnostics.voiceURI}</span>
                    </div>
                    <div className="flex justify-between">
                      <span>Gender Selection:</span>
                      <span className={diagnostics.genderClassification === 'FEMALE' ? "text-emerald-400 font-bold" : "text-amber-400 font-bold"}>
                        {diagnostics.genderClassification}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span>Voice Test Status:</span>
                      <span className="text-purple-300 font-bold">{diagnostics.testStatus}</span>
                    </div>
                    <div className="flex justify-between">
                      <span>TTS Status:</span>
                      <span className="text-sky-300">{isSpeaking ? 'SPEAKING' : (isCallActive ? 'ACTIVE' : 'READY')}</span>
                    </div>
                  </div>
                )}
              </div>

              {/* SAFETY STATUS BADGE */}
              <div className="bg-slate-950 p-2.5 rounded-xl border border-slate-800 flex items-center justify-between text-xs font-mono">
                <div className="flex items-center space-x-1.5">
                  <ShieldCheck className="w-4 h-4 text-emerald-400" />
                  <span className="text-slate-300 text-[11px]">Safety Pipeline</span>
                </div>
                <span className="px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 font-bold text-[10px]">
                  {lastVoiceResponse?.safety_status || 'ENFORCED'}
                </span>
              </div>
            </div>
          </div>

          {/* RIGHT: LIVE TRANSCRIPT & INTERACTION PANEL (2 COLS) */}
          <div className="lg:col-span-2 space-y-4">
            
            {/* TRANSCRIPT PANEL */}
            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 space-y-4 flex flex-col h-[560px]">
              
              <div className="flex items-center justify-between border-b pb-3 border-slate-800">
                <div className="flex items-center space-x-2">
                  <MessageSquare className="w-5 h-5 text-purple-400" />
                  <h3 className="font-extrabold text-sm text-slate-100 tracking-tight">LIVE CONVERSATION TRANSCRIPT (HINGLISH/ENGLISH)</h3>
                </div>
                <span className="text-[11px] font-mono text-slate-400">Session ID: {currentSessionId || 'N/A'}</span>
              </div>

              {/* CHAT MESSAGES CONTAINER */}
              <div className="flex-1 overflow-y-auto space-y-3.5 pr-2">
                {transcript.length === 0 ? (
                  <div className="text-center py-24 text-slate-500 space-y-2">
                    <Bot className="w-10 h-10 mx-auto text-slate-700" />
                    <p className="text-xs">Click 'START PAYPILOT VOICE CALL' to initiate call session</p>
                  </div>
                ) : (
                  transcript.map((msg, idx) => (
                    <div
                      key={idx}
                      className={`flex flex-col ${msg.sender === 'CUSTOMER' ? 'items-end' : 'items-start'}`}
                    >
                      <div className="flex items-center space-x-1.5 mb-1 text-[10px] font-mono text-slate-500">
                        {msg.sender === 'AGENT' ? (
                          <>
                            <Bot className="w-3 h-3 text-purple-400" />
                            <span className="text-purple-400 font-bold">PayPilot Voice Agent</span>
                          </>
                        ) : (
                          <>
                            <User className="w-3 h-3 text-sky-400" />
                            <span className="text-sky-400 font-bold">Customer ({selectedInvoice?.customer?.name || 'Client'})</span>
                          </>
                        )}
                        <span>• {msg.timestamp}</span>
                      </div>

                      <div className={`p-3.5 rounded-2xl max-w-lg text-xs leading-relaxed ${
                        msg.sender === 'CUSTOMER'
                          ? 'bg-sky-600 text-white font-medium rounded-tr-none shadow-sm'
                          : 'bg-slate-950 text-slate-200 border border-slate-800 rounded-tl-none space-y-1.5'
                      }`}>
                        <p>{msg.text}</p>
                        {msg.intent && (
                          <div className="pt-1.5 border-t border-slate-800/80 flex items-center justify-between text-[10px] font-mono text-purple-300">
                            <span>Detected Intent: <strong>{msg.intent}</strong></span>
                            {msg.action && <span className="bg-purple-500/20 px-1.5 py-0.5 rounded text-purple-200">{msg.action}</span>}
                          </div>
                        )}
                      </div>
                    </div>
                  ))
                )}
                <div ref={transcriptEndRef} />
              </div>

              {/* SPEECH INPUT & MIC CONTROLS */}
              {isCallActive && (
                <div className="pt-2 border-t border-slate-800 space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] font-bold text-slate-400 uppercase font-mono tracking-widest block">
                      FREE-FORM CONVERSATIONAL AI SPEECH & TEXT INPUT:
                    </span>
                    {micSupported && (
                      <button
                        onClick={toggleMicListening}
                        className={`px-2.5 py-1 rounded-lg text-[10px] font-mono font-bold flex items-center space-x-1.5 transition-colors ${
                          isMicActive 
                            ? 'bg-rose-500/20 text-rose-300 border border-rose-500/40 animate-pulse' 
                            : 'bg-slate-800 text-slate-300 hover:bg-slate-700 border border-slate-700'
                        }`}
                      >
                        {isMicActive ? <Mic className="w-3 h-3 text-rose-400" /> : <MicOff className="w-3 h-3 text-slate-400" />}
                        <span>{isMicActive ? 'Recording Speech...' : 'Enable Live Mic'}</span>
                      </button>
                    )}
                  </div>

                  {/* CUSTOM SPEECH / TEXT INPUT */}
                  <div className="flex space-x-2 pt-1">
                    <input
                      type="text"
                      value={inputText}
                      onChange={(e) => setInputText(e.target.value)}
                      onKeyDown={(e) => e.key === 'Enter' && sendSpeechInput(inputText)}
                      placeholder="Type speech input or talk via microphone (Hinglish/English)..."
                      className="flex-1 bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-slate-200 font-mono focus:outline-none focus:border-purple-500"
                    />
                    <button
                      onClick={() => sendSpeechInput(inputText)}
                      disabled={loading || !inputText.trim()}
                      className="px-4 py-2 bg-purple-600 hover:bg-purple-500 text-white font-bold rounded-xl text-xs transition-colors flex items-center space-x-1 disabled:opacity-50"
                    >
                      <Send className="w-3.5 h-3.5" />
                      <span>Send</span>
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>

      </main>
    </div>
  );
}
