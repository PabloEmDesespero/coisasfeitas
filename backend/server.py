from fastapi import FastAPI, APIRouter, HTTPException
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime
import aiohttp
import asyncio
import json
import pandas as pd
import numpy as np
import yfinance as yf
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.patches import Rectangle
from PIL import Image, ImageDraw, ImageFont
import io
import base64
import ta
from io import StringIO
import requests

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# LM Studio Configuration
LM_STUDIO_URL = "http://127.0.0.1:1234"

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Models
class TradingQuery(BaseModel):
    question: str
    symbol: str = "BTC-USD"

class TradingResponse(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    question: str
    symbol: str
    analysis: str
    recommendation: str
    confidence: float
    technical_data: Dict[str, Any]
    ascii_chart: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class StatusCheck(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    client_name: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class StatusCheckCreate(BaseModel):
    client_name: str

# ASCII Art Generator
def generate_ascii_chart(data: pd.DataFrame, symbol: str, width: int = 80, height: int = 20) -> str:
    """Generate ASCII representation of candlestick chart"""
    try:
        # Get last 20 data points for chart
        chart_data = data.tail(20)
        
        if len(chart_data) < 5:
            return "Dados insuficientes para gerar gráfico"
        
        # Normalize prices to fit ASCII height
        min_price = chart_data[['Low', 'High', 'Open', 'Close']].min().min()
        max_price = chart_data[['Low', 'High', 'Open', 'Close']].max().max()
        price_range = max_price - min_price
        
        if price_range == 0:
            return "Range de preços insuficiente"
        
        # Create ASCII chart
        chart_lines = []
        
        # Header
        chart_lines.append(f"═══ {symbol} - Gráfico de Candlestick (ASCII) ═══")
        chart_lines.append(f"Máx: ${max_price:.2f} | Mín: ${min_price:.2f}")
        chart_lines.append("")
        
        # Create simple price representation
        for i, (_, row) in enumerate(chart_data.iterrows()):
            open_price = row['Open']
            close_price = row['Close']
            high_price = row['High']
            low_price = row['Low']
            
            # Determine candle direction
            is_green = close_price >= open_price
            
            # Normalize positions (0-height)
            high_pos = int((high_price - min_price) / price_range * height)
            low_pos = int((low_price - min_price) / price_range * height)
            open_pos = int((open_price - min_price) / price_range * height)
            close_pos = int((close_price - min_price) / price_range * height)
            
            # Create candlestick representation
            if is_green:
                candle = "▲" if close_pos > open_pos else "─"
            else:
                candle = "▼" if close_pos < open_pos else "─"
            
            price_str = f"{close_price:.1f}"
            chart_lines.append(f"{i:2d}: {candle} {price_str:>8s}")
        
        # Add recent trend
        recent_change = ((chart_data['Close'].iloc[-1] - chart_data['Close'].iloc[-5]) / chart_data['Close'].iloc[-5]) * 100
        trend_emoji = "🚀" if recent_change > 2 else "📈" if recent_change > 0 else "📉" if recent_change < -2 else "➡️"
        
        chart_lines.append("")
        chart_lines.append(f"Tendência: {trend_emoji} {recent_change:+.2f}%")
        
        return "\n".join(chart_lines)
    
    except Exception as e:
        return f"Erro ao gerar gráfico ASCII: {str(e)}"

# Technical Analysis
def calculate_technical_indicators(data: pd.DataFrame) -> Dict[str, Any]:
    """Calculate technical indicators"""
    try:
        if len(data) < 20:
            return {"error": "Dados insuficientes para análise técnica"}
        
        # Calculate indicators
        data['RSI'] = ta.momentum.RSIIndicator(data['Close']).rsi()
        
        # MACD
        macd = ta.trend.MACD(data['Close'])
        data['MACD'] = macd.macd()
        data['MACD_signal'] = macd.macd_signal()
        data['MACD_histogram'] = macd.macd_diff()
        
        # Bollinger Bands
        bollinger = ta.volatility.BollingerBands(data['Close'])
        data['BB_upper'] = bollinger.bollinger_hband()
        data['BB_lower'] = bollinger.bollinger_lband()
        data['BB_middle'] = bollinger.bollinger_mavg()
        
        # Simple Moving Averages
        data['SMA_20'] = ta.trend.SMAIndicator(data['Close'], window=20).sma_indicator()
        data['SMA_50'] = ta.trend.SMAIndicator(data['Close'], window=50).sma_indicator() if len(data) >= 50 else None
        
        # Current values
        latest = data.iloc[-1]
        
        indicators = {
            "RSI": {
                "value": float(latest['RSI']) if not pd.isna(latest['RSI']) else None,
                "signal": "SOBRECOMPRA" if latest['RSI'] > 70 else "SOBREVENDA" if latest['RSI'] < 30 else "NEUTRO"
            },
            "MACD": {
                "macd": float(latest['MACD']) if not pd.isna(latest['MACD']) else None,
                "signal": float(latest['MACD_signal']) if not pd.isna(latest['MACD_signal']) else None,
                "histogram": float(latest['MACD_histogram']) if not pd.isna(latest['MACD_histogram']) else None,
                "trend": "ALTA" if latest['MACD'] > latest['MACD_signal'] else "BAIXA"
            },
            "Bollinger_Bands": {
                "current_price": float(latest['Close']),
                "upper_band": float(latest['BB_upper']) if not pd.isna(latest['BB_upper']) else None,
                "lower_band": float(latest['BB_lower']) if not pd.isna(latest['BB_lower']) else None,
                "position": "ACIMA" if latest['Close'] > latest['BB_upper'] else "ABAIXO" if latest['Close'] < latest['BB_lower'] else "DENTRO"
            },
            "Moving_Averages": {
                "SMA_20": float(latest['SMA_20']) if not pd.isna(latest['SMA_20']) else None,
                "SMA_50": float(latest['SMA_50']) if not pd.isna(latest['SMA_50']) and latest['SMA_50'] is not None else None,
                "price_vs_sma20": "ACIMA" if latest['Close'] > latest['SMA_20'] else "ABAIXO"
            },
            "Volume": {
                "current": int(latest['Volume']) if 'Volume' in latest and not pd.isna(latest['Volume']) else 0,
                "average": int(data['Volume'].tail(20).mean()) if 'Volume' in data else 0
            },
            "Price_Action": {
                "current_price": float(latest['Close']),
                "daily_change": float(latest['Close'] - latest['Open']),
                "daily_change_pct": float((latest['Close'] - latest['Open']) / latest['Open'] * 100),
                "high": float(latest['High']),
                "low": float(latest['Low'])
            }
        }
        
        return indicators
    
    except Exception as e:
        return {"error": f"Erro no cálculo dos indicadores: {str(e)}"}

# LM Studio Integration
async def query_lm_studio(prompt: str) -> str:
    """Query LM Studio with trading analysis prompt"""
    try:
        async with aiohttp.ClientSession() as session:
            payload = {
                "model": "gemma-3-gaia-pt-br-4b-instruct",
                "messages": [
                    {
                        "role": "system", 
                        "content": """Você é um especialista em análise de trading de criptomoedas e análise técnica. 
                        
Use estas 7 Leis para suas análises:

1. Lei de Consequência (→): Se algo é feito no mercado, algo retorna. Analise causa e efeito.
2. Lei da Preservação (∧): Manter posição exige coerência entre indicadores.
3. Lei de Transformação (¬): Toda mudança exige negar padrão anterior (bear→bull).
4. Lei do Trabalho (∨): Escolher agir ou omitir - o mercado sempre responde.
5. Lei do Progresso (↔): Evolução só ocorre quando análise e ação andam juntas.
6. Lei de Entropia (∅): Posições negligenciadas tendem ao caos - stop loss obrigatório.
7. Lei de Equivalência (Δ): Toda conquista exige renúncia proporcional - risco x retorno.

Seja direto, prático e explique sua recomendação usando essas leis."""
                    },
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.7,
                "max_tokens": 800,
                "stream": False
            }
            
            async with session.post(
                f"{LM_STUDIO_URL}/v1/chat/completions",
                headers={"Content-Type": "application/json"},
                json=payload,
                timeout=30
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    return result['choices'][0]['message']['content']
                else:
                    return f"Erro na comunicação com LM Studio: {response.status}"
                    
    except Exception as e:
        return f"Erro ao conectar com LM Studio: {str(e)}"

# Main trading analysis function
async def analyze_trading_symbol(symbol: str, question: str) -> TradingResponse:
    """Main function to analyze trading symbol"""
    try:
        # Fetch data from Yahoo Finance
        ticker = yf.Ticker(symbol)
        data = ticker.history(period="3mo", interval="1d")
        
        if data.empty:
            raise HTTPException(status_code=404, detail=f"Dados não encontrados para {symbol}")
        
        # Calculate technical indicators
        technical_data = calculate_technical_indicators(data)
        
        # Generate ASCII chart
        ascii_chart = generate_ascii_chart(data, symbol)
        
        # Prepare prompt for LM Studio
        current_price = data['Close'].iloc[-1]
        price_change = ((data['Close'].iloc[-1] - data['Close'].iloc[-2]) / data['Close'].iloc[-2]) * 100
        
        prompt = f"""ANÁLISE DE TRADING SOLICITADA:

PERGUNTA: {question}

ATIVO: {symbol}
PREÇO ATUAL: ${current_price:.2f}
VARIAÇÃO DIÁRIA: {price_change:+.2f}%

GRÁFICO ASCII:
{ascii_chart}

INDICADORES TÉCNICOS:
{json.dumps(technical_data, indent=2, ensure_ascii=False)}

CONTEXTO DE MERCADO:
- Volume atual vs média: {technical_data.get('Volume', {}).get('current', 0)} vs {technical_data.get('Volume', {}).get('average', 0)}
- RSI: {technical_data.get('RSI', {}).get('value', 'N/A')} ({technical_data.get('RSI', {}).get('signal', 'N/A')})
- MACD: {technical_data.get('MACD', {}).get('trend', 'N/A')}
- Bollinger Bands: {technical_data.get('Bollinger_Bands', {}).get('position', 'N/A')}

Por favor, analise usando as 7 Leis e forneça:
1. Análise detalhada da situação atual
2. Recomendação clara (COMPRAR/VENDER/AGUARDAR)  
3. Nível de confiança (0-100%)
4. Justificativa baseada nas leis

Seja prático e direto na resposta."""

        # Query LM Studio
        ai_response = await query_lm_studio(prompt)
        
        # Extract confidence and recommendation from AI response
        confidence = 75.0  # Default confidence
        recommendation = "AGUARDAR"  # Default recommendation
        
        # Simple pattern matching for recommendation
        response_lower = ai_response.lower()
        if "comprar" in response_lower or "buy" in response_lower:
            recommendation = "COMPRAR"
        elif "vender" in response_lower or "sell" in response_lower:
            recommendation = "VENDER"
        
        # Simple pattern matching for confidence
        if "alta confiança" in response_lower or "muito confiante" in response_lower:
            confidence = 90.0
        elif "baixa confiança" in response_lower or "incerto" in response_lower:
            confidence = 50.0
        
        return TradingResponse(
            question=question,
            symbol=symbol,
            analysis=ai_response,
            recommendation=recommendation,
            confidence=confidence,
            technical_data=technical_data,
            ascii_chart=ascii_chart
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro na análise: {str(e)}")

# API Routes
@api_router.post("/trading/analyze", response_model=TradingResponse)
async def analyze_trading(query: TradingQuery):
    """Analyze trading symbol with AI"""
    response = await analyze_trading_symbol(query.symbol, query.question)
    
    # Save to database
    await db.trading_analyses.insert_one(response.dict())
    
    return response

@api_router.get("/trading/history", response_model=List[TradingResponse])
async def get_trading_history():
    """Get trading analysis history"""
    analyses = await db.trading_analyses.find().sort("timestamp", -1).to_list(50)
    return [TradingResponse(**analysis) for analysis in analyses]

@api_router.get("/trading/symbols")
async def get_available_symbols():
    """Get list of available trading symbols"""
    symbols = [
        {"symbol": "BTC-USD", "name": "Bitcoin", "type": "Crypto"},
        {"symbol": "ETH-USD", "name": "Ethereum", "type": "Crypto"},
        {"symbol": "ADA-USD", "name": "Cardano", "type": "Crypto"},
        {"symbol": "SOL-USD", "name": "Solana", "type": "Crypto"},
        {"symbol": "AAPL", "name": "Apple", "type": "Stock"},
        {"symbol": "GOOGL", "name": "Google", "type": "Stock"},
        {"symbol": "TSLA", "name": "Tesla", "type": "Stock"},
        {"symbol": "MSFT", "name": "Microsoft", "type": "Stock"},
        {"symbol": "PETR4.SA", "name": "Petrobras", "type": "Stock BR"},
        {"symbol": "VALE3.SA", "name": "Vale", "type": "Stock BR"},
        {"symbol": "ITUB4.SA", "name": "Itaú", "type": "Stock BR"}
    ]
    return symbols

@api_router.get("/")
async def root():
    return {"message": "Bot de Trading com IA - Sistema Ativo"}

@api_router.post("/status", response_model=StatusCheck)
async def create_status_check(input: StatusCheckCreate):
    status_dict = input.dict()
    status_obj = StatusCheck(**status_dict)
    _ = await db.status_checks.insert_one(status_obj.dict())
    return status_obj

@api_router.get("/status", response_model=List[StatusCheck])
async def get_status_checks():
    status_checks = await db.status_checks.find().to_list(1000)
    return [StatusCheck(**status_check) for status_check in status_checks]

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()