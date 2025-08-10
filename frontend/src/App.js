import React, { useState, useEffect, useRef } from "react";
import "./App.css";
import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

function App() {
  const [messages, setMessages] = useState([]);
  const [inputMessage, setInputMessage] = useState("");
  const [selectedSymbol, setSelectedSymbol] = useState("BTC-USD");
  const [availableSymbols, setAvailableSymbols] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [history, setHistory] = useState([]);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Load available symbols
  useEffect(() => {
    const loadSymbols = async () => {
      try {
        const response = await axios.get(`${API}/trading/symbols`);
        setAvailableSymbols(response.data);
      } catch (error) {
        console.error("Erro ao carregar símbolos:", error);
      }
    };
    loadSymbols();
  }, []);

  // Load history
  useEffect(() => {
    const loadHistory = async () => {
      try {
        const response = await axios.get(`${API}/trading/history`);
        setHistory(response.data.slice(0, 5)); // Show last 5 analyses
      } catch (error) {
        console.error("Erro ao carregar histórico:", error);
      }
    };
    loadHistory();
  }, [messages]);

  const sendMessage = async () => {
    if (!inputMessage.trim()) return;

    const userMessage = {
      id: Date.now(),
      text: inputMessage,
      sender: "user",
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMessage]);
    setIsLoading(true);

    try {
      const response = await axios.post(`${API}/trading/analyze`, {
        question: inputMessage,
        symbol: selectedSymbol
      });

      const botMessage = {
        id: Date.now() + 1,
        sender: "bot",
        data: response.data,
        timestamp: new Date()
      };

      setMessages(prev => [...prev, botMessage]);
    } catch (error) {
      const errorMessage = {
        id: Date.now() + 1,
        text: `Erro na análise: ${error.response?.data?.detail || error.message}`,
        sender: "error",
        timestamp: new Date()
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
      setInputMessage("");
    }
  };

  const formatConfidence = (confidence) => {
    if (confidence >= 80) return { text: "Alta", color: "text-green-600" };
    if (confidence >= 60) return { text: "Média", color: "text-yellow-600" };
    return { text: "Baixa", color: "text-red-600" };
  };

  const getRecommendationColor = (recommendation) => {
    switch (recommendation) {
      case "COMPRAR": return "bg-green-100 text-green-800 border-green-200";
      case "VENDER": return "bg-red-100 text-red-800 border-red-200";
      default: return "bg-yellow-100 text-yellow-800 border-yellow-200";
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-blue-900 to-purple-900">
      {/* Header */}
      <header className="bg-black/30 backdrop-blur-sm border-b border-white/10">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <h1 className="text-2xl font-bold text-white flex items-center gap-3">
              <span className="text-3xl">🤖</span>
              Bot de Trading com IA
            </h1>
            <div className="flex items-center gap-4">
              <select
                value={selectedSymbol}
                onChange={(e) => setSelectedSymbol(e.target.value)}
                className="bg-white/10 text-white border border-white/20 rounded-lg px-3 py-2 backdrop-blur-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                {availableSymbols.map((symbol) => (
                  <option key={symbol.symbol} value={symbol.symbol} className="bg-gray-800">
                    {symbol.symbol} - {symbol.name} ({symbol.type})
                  </option>
                ))}
              </select>
            </div>
          </div>
        </div>
      </header>

      <div className="container mx-auto px-4 py-6">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          
          {/* Chat Area */}
          <div className="lg:col-span-2">
            <div className="bg-white/10 backdrop-blur-sm rounded-2xl border border-white/20 h-[600px] flex flex-col">
              <div className="p-4 border-b border-white/10">
                <h2 className="text-xl font-semibold text-white flex items-center gap-2">
                  💬 Converse com a IA sobre Trading
                  <span className="text-sm text-white/60">({selectedSymbol})</span>
                </h2>
              </div>

              {/* Messages */}
              <div className="flex-1 overflow-y-auto p-4 space-y-4">
                {messages.length === 0 && (
                  <div className="text-center text-white/60 py-8">
                    <div className="text-4xl mb-4">🚀</div>
                    <p className="text-lg">Olá! Sou seu assistente de trading com IA.</p>
                    <p className="text-sm mt-2">Pergunte algo como: "Devo comprar Bitcoin agora?" ou "Qual a análise técnica do ETH?"</p>
                  </div>
                )}

                {messages.map((message) => (
                  <div key={message.id} className={`flex ${message.sender === 'user' ? 'justify-end' : 'justify-start'}`}>
                    {message.sender === 'user' ? (
                      <div className="bg-blue-500 text-white rounded-2xl px-4 py-2 max-w-xs lg:max-w-md">
                        <p>{message.text}</p>
                        <span className="text-xs text-white/70 mt-1 block">
                          {message.timestamp.toLocaleTimeString()}
                        </span>
                      </div>
                    ) : message.sender === 'error' ? (
                      <div className="bg-red-500/20 border border-red-500/30 text-red-200 rounded-2xl px-4 py-2 max-w-xs lg:max-w-md">
                        <p>{message.text}</p>
                      </div>
                    ) : (
                      <div className="bg-white/10 text-white rounded-2xl p-4 max-w-full">
                        <div className="flex items-center gap-2 mb-3">
                          <span className="text-lg">🤖</span>
                          <span className="font-semibold">Análise da IA</span>
                          <span className={`px-2 py-1 rounded text-xs border ${getRecommendationColor(message.data.recommendation)}`}>
                            {message.data.recommendation}
                          </span>
                        </div>

                        {/* ASCII Chart */}
                        <div className="bg-black/30 rounded-lg p-3 mb-3 font-mono text-sm text-green-400 overflow-x-auto">
                          <pre>{message.data.ascii_chart}</pre>
                        </div>

                        {/* Analysis */}
                        <div className="mb-3">
                          <h4 className="font-semibold mb-2 text-white">📊 Análise:</h4>
                          <p className="text-white/80 text-sm whitespace-pre-wrap">{message.data.analysis}</p>
                        </div>

                        {/* Confidence */}
                        <div className="flex items-center justify-between text-sm">
                          <span className="text-white/60">
                            {message.data.timestamp && new Date(message.data.timestamp).toLocaleString()}
                          </span>
                          <span className={`font-semibold ${formatConfidence(message.data.confidence).color}`}>
                            Confiança: {formatConfidence(message.data.confidence).text} ({message.data.confidence.toFixed(0)}%)
                          </span>
                        </div>
                      </div>
                    )}
                  </div>
                ))}

                {isLoading && (
                  <div className="flex justify-start">
                    <div className="bg-white/10 text-white rounded-2xl px-4 py-2 flex items-center gap-2">
                      <div className="animate-spin rounded-full h-4 w-4 border-2 border-white/30 border-t-white"></div>
                      <span>Analisando mercado...</span>
                    </div>
                  </div>
                )}

                <div ref={messagesEndRef} />
              </div>

              {/* Input */}
              <div className="p-4 border-t border-white/10">
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={inputMessage}
                    onChange={(e) => setInputMessage(e.target.value)}
                    onKeyPress={(e) => e.key === 'Enter' && !isLoading && sendMessage()}
                    placeholder={`Pergunte sobre ${selectedSymbol}...`}
                    disabled={isLoading}
                    className="flex-1 bg-white/10 text-white border border-white/20 rounded-lg px-4 py-2 backdrop-blur-sm focus:outline-none focus:ring-2 focus:ring-blue-500 placeholder-white/50"
                  />
                  <button
                    onClick={sendMessage}
                    disabled={isLoading || !inputMessage.trim()}
                    className="bg-blue-500 hover:bg-blue-600 disabled:bg-gray-500 disabled:cursor-not-allowed text-white px-6 py-2 rounded-lg transition-colors duration-200 font-semibold"
                  >
                    {isLoading ? "⏳" : "📤"}
                  </button>
                </div>
              </div>
            </div>
          </div>

          {/* Sidebar */}
          <div className="space-y-4">
            {/* Quick Actions */}
            <div className="bg-white/10 backdrop-blur-sm rounded-2xl border border-white/20 p-4">
              <h3 className="font-semibold text-white mb-3 flex items-center gap-2">
                ⚡ Perguntas Rápidas
              </h3>
              <div className="space-y-2">
                {[
                  "Devo comprar agora?",
                  "Qual a análise técnica?",
                  "Quando vender?",
                  "Qual o risco atual?"
                ].map((question) => (
                  <button
                    key={question}
                    onClick={() => setInputMessage(question)}
                    className="w-full text-left bg-white/5 hover:bg-white/10 text-white/80 px-3 py-2 rounded-lg text-sm transition-colors duration-200"
                  >
                    {question}
                  </button>
                ))}
              </div>
            </div>

            {/* Recent History */}
            <div className="bg-white/10 backdrop-blur-sm rounded-2xl border border-white/20 p-4">
              <h3 className="font-semibold text-white mb-3 flex items-center gap-2">
                📈 Análises Recentes
              </h3>
              <div className="space-y-2">
                {history.map((item) => (
                  <div key={item.id} className="bg-white/5 rounded-lg p-3 text-sm">
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-white font-medium">{item.symbol}</span>
                      <span className={`px-2 py-1 rounded text-xs ${getRecommendationColor(item.recommendation)}`}>
                        {item.recommendation}
                      </span>
                    </div>
                    <p className="text-white/60 text-xs">
                      {new Date(item.timestamp).toLocaleDateString()}
                    </p>
                  </div>
                ))}
              </div>
            </div>

            {/* System Status */}
            <div className="bg-white/10 backdrop-blur-sm rounded-2xl border border-white/20 p-4">
              <h3 className="font-semibold text-white mb-3 flex items-center gap-2">
                🔧 Status do Sistema
              </h3>
              <div className="space-y-2 text-sm">
                <div className="flex items-center justify-between">
                  <span className="text-white/70">LM Studio</span>
                  <span className="text-green-400 flex items-center gap-1">
                    <div className="w-2 h-2 bg-green-400 rounded-full"></div>
                    Ativo
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-white/70">Dados de Mercado</span>
                  <span className="text-green-400 flex items-center gap-1">
                    <div className="w-2 h-2 bg-green-400 rounded-full"></div>
                    Online
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-white/70">IA Gemma 3</span>
                  <span className="text-green-400 flex items-center gap-1">
                    <div className="w-2 h-2 bg-green-400 rounded-full"></div>
                    Pronto
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;