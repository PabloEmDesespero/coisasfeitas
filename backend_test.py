#!/usr/bin/env python3
"""
Backend Testing Suite for Trading Bot
Tests all backend functionality including API endpoints, LM Studio integration, and data collection
"""

import requests
import json
import asyncio
import aiohttp
import time
from datetime import datetime
from typing import Dict, Any, List
import sys
import os

# Get backend URL from frontend .env
BACKEND_URL = "https://f3913996-cc33-4a44-9d29-6dc200a6deac.preview.emergentagent.com"
LM_STUDIO_URL = "http://127.0.0.1:1234"

class TradingBotTester:
    def __init__(self):
        self.backend_url = BACKEND_URL
        self.lm_studio_url = LM_STUDIO_URL
        self.test_results = []
        
    def log_test(self, test_name: str, success: bool, message: str, details: Any = None):
        """Log test results"""
        result = {
            "test": test_name,
            "success": success,
            "message": message,
            "details": details,
            "timestamp": datetime.now().isoformat()
        }
        self.test_results.append(result)
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} - {test_name}: {message}")
        if details and not success:
            print(f"   Details: {details}")
    
    def test_basic_connectivity(self):
        """Test 1: Basic connectivity to /api/ endpoint"""
        print("\n=== TESTE 1: CONECTIVIDADE BÁSICA ===")
        
        try:
            response = requests.get(f"{self.backend_url}/api/", timeout=10)
            if response.status_code == 200:
                data = response.json()
                if "message" in data:
                    self.log_test(
                        "Basic Connectivity", 
                        True, 
                        f"Backend respondendo corretamente: {data['message']}"
                    )
                else:
                    self.log_test(
                        "Basic Connectivity", 
                        False, 
                        "Resposta não contém mensagem esperada",
                        data
                    )
            else:
                self.log_test(
                    "Basic Connectivity", 
                    False, 
                    f"Status code inesperado: {response.status_code}",
                    response.text
                )
        except requests.exceptions.RequestException as e:
            self.log_test(
                "Basic Connectivity", 
                False, 
                "Erro de conexão com backend",
                str(e)
            )
    
    def test_lm_studio_connectivity(self):
        """Test 2: LM Studio integration"""
        print("\n=== TESTE 2: INTEGRAÇÃO LM STUDIO ===")
        
        try:
            # Test direct connection to LM Studio
            response = requests.get(f"{self.lm_studio_url}/v1/models", timeout=5)
            if response.status_code == 200:
                models = response.json()
                self.log_test(
                    "LM Studio Direct Connection", 
                    True, 
                    f"LM Studio respondendo com {len(models.get('data', []))} modelos"
                )
            else:
                self.log_test(
                    "LM Studio Direct Connection", 
                    False, 
                    f"LM Studio não respondeu corretamente: {response.status_code}",
                    response.text
                )
        except requests.exceptions.RequestException as e:
            self.log_test(
                "LM Studio Direct Connection", 
                False, 
                "LM Studio não está acessível (esperado se não estiver rodando)",
                str(e)
            )
    
    def test_trading_symbols_api(self):
        """Test 3: GET /api/trading/symbols"""
        print("\n=== TESTE 3: API DE SÍMBOLOS ===")
        
        try:
            response = requests.get(f"{self.backend_url}/api/trading/symbols", timeout=10)
            if response.status_code == 200:
                symbols = response.json()
                if isinstance(symbols, list) and len(symbols) > 0:
                    btc_found = any(s.get('symbol') == 'BTC-USD' for s in symbols)
                    self.log_test(
                        "Trading Symbols API", 
                        True, 
                        f"Retornou {len(symbols)} símbolos, BTC-USD {'encontrado' if btc_found else 'não encontrado'}"
                    )
                else:
                    self.log_test(
                        "Trading Symbols API", 
                        False, 
                        "Lista de símbolos vazia ou formato inválido",
                        symbols
                    )
            else:
                self.log_test(
                    "Trading Symbols API", 
                    False, 
                    f"Status code inesperado: {response.status_code}",
                    response.text
                )
        except requests.exceptions.RequestException as e:
            self.log_test(
                "Trading Symbols API", 
                False, 
                "Erro ao acessar API de símbolos",
                str(e)
            )
    
    def test_trading_analyze_api(self):
        """Test 4: POST /api/trading/analyze"""
        print("\n=== TESTE 4: API DE ANÁLISE ===")
        
        test_data = {
            "question": "Devo comprar Bitcoin agora?",
            "symbol": "BTC-USD"
        }
        
        try:
            response = requests.post(
                f"{self.backend_url}/api/trading/analyze",
                json=test_data,
                timeout=60  # Longer timeout for AI analysis
            )
            
            if response.status_code == 200:
                analysis = response.json()
                required_fields = ['id', 'question', 'symbol', 'analysis', 'recommendation', 'confidence', 'technical_data', 'ascii_chart']
                missing_fields = [field for field in required_fields if field not in analysis]
                
                if not missing_fields:
                    self.log_test(
                        "Trading Analysis API", 
                        True, 
                        f"Análise gerada com sucesso. Recomendação: {analysis.get('recommendation', 'N/A')}, Confiança: {analysis.get('confidence', 'N/A')}%"
                    )
                else:
                    self.log_test(
                        "Trading Analysis API", 
                        False, 
                        f"Campos obrigatórios ausentes: {missing_fields}",
                        analysis
                    )
            else:
                self.log_test(
                    "Trading Analysis API", 
                    False, 
                    f"Status code inesperado: {response.status_code}",
                    response.text
                )
        except requests.exceptions.RequestException as e:
            self.log_test(
                "Trading Analysis API", 
                False, 
                "Erro ao executar análise de trading",
                str(e)
            )
    
    def test_trading_history_api(self):
        """Test 5: GET /api/trading/history"""
        print("\n=== TESTE 5: API DE HISTÓRICO ===")
        
        try:
            response = requests.get(f"{self.backend_url}/api/trading/history", timeout=10)
            if response.status_code == 200:
                history = response.json()
                if isinstance(history, list):
                    self.log_test(
                        "Trading History API", 
                        True, 
                        f"Histórico retornado com {len(history)} análises"
                    )
                else:
                    self.log_test(
                        "Trading History API", 
                        False, 
                        "Formato de resposta inválido (não é lista)",
                        history
                    )
            else:
                self.log_test(
                    "Trading History API", 
                    False, 
                    f"Status code inesperado: {response.status_code}",
                    response.text
                )
        except requests.exceptions.RequestException as e:
            self.log_test(
                "Trading History API", 
                False, 
                "Erro ao acessar histórico de análises",
                str(e)
            )
    
    def test_yahoo_finance_integration(self):
        """Test 6: Yahoo Finance data collection"""
        print("\n=== TESTE 6: INTEGRAÇÃO YAHOO FINANCE ===")
        
        try:
            import yfinance as yf
            
            # Test data fetching
            ticker = yf.Ticker("BTC-USD")
            data = ticker.history(period="5d", interval="1d")
            
            if not data.empty and len(data) > 0:
                latest_price = data['Close'].iloc[-1]
                self.log_test(
                    "Yahoo Finance Integration", 
                    True, 
                    f"Dados do BTC-USD coletados com sucesso. Preço atual: ${latest_price:.2f}"
                )
            else:
                self.log_test(
                    "Yahoo Finance Integration", 
                    False, 
                    "Nenhum dado retornado do Yahoo Finance",
                    None
                )
        except Exception as e:
            self.log_test(
                "Yahoo Finance Integration", 
                False, 
                "Erro na integração com Yahoo Finance",
                str(e)
            )
    
    def test_technical_indicators(self):
        """Test 7: Technical indicators calculation"""
        print("\n=== TESTE 7: INDICADORES TÉCNICOS ===")
        
        try:
            import yfinance as yf
            import ta
            import pandas as pd
            
            # Get data
            ticker = yf.Ticker("BTC-USD")
            data = ticker.history(period="3mo", interval="1d")
            
            if len(data) >= 20:
                # Test RSI calculation
                data['RSI'] = ta.momentum.RSIIndicator(data['Close']).rsi()
                
                # Test MACD
                macd = ta.trend.MACD(data['Close'])
                data['MACD'] = macd.macd()
                
                # Test Bollinger Bands
                bollinger = ta.volatility.BollingerBands(data['Close'])
                data['BB_upper'] = bollinger.bollinger_hband()
                
                # Check if indicators were calculated
                rsi_valid = not data['RSI'].iloc[-1] is None and not pd.isna(data['RSI'].iloc[-1])
                macd_valid = not data['MACD'].iloc[-1] is None and not pd.isna(data['MACD'].iloc[-1])
                bb_valid = not data['BB_upper'].iloc[-1] is None and not pd.isna(data['BB_upper'].iloc[-1])
                
                if rsi_valid and macd_valid and bb_valid:
                    self.log_test(
                        "Technical Indicators", 
                        True, 
                        f"Indicadores calculados: RSI={data['RSI'].iloc[-1]:.2f}, MACD={data['MACD'].iloc[-1]:.4f}"
                    )
                else:
                    self.log_test(
                        "Technical Indicators", 
                        False, 
                        f"Alguns indicadores falharam: RSI={rsi_valid}, MACD={macd_valid}, BB={bb_valid}",
                        None
                    )
            else:
                self.log_test(
                    "Technical Indicators", 
                    False, 
                    "Dados insuficientes para calcular indicadores técnicos",
                    f"Apenas {len(data)} dias de dados"
                )
        except Exception as e:
            self.log_test(
                "Technical Indicators", 
                False, 
                "Erro no cálculo de indicadores técnicos",
                str(e)
            )
    
    def test_database_operations(self):
        """Test 8: Database CRUD operations"""
        print("\n=== TESTE 8: OPERAÇÕES DE BANCO DE DADOS ===")
        
        # Test status endpoint (which uses MongoDB)
        try:
            # Test POST to create status check
            test_status = {
                "client_name": "test_client_backend_testing"
            }
            
            response = requests.post(
                f"{self.backend_url}/api/status",
                json=test_status,
                timeout=10
            )
            
            if response.status_code == 200:
                created_status = response.json()
                if 'id' in created_status and 'client_name' in created_status:
                    # Test GET to retrieve status checks
                    get_response = requests.get(f"{self.backend_url}/api/status", timeout=10)
                    if get_response.status_code == 200:
                        status_list = get_response.json()
                        test_found = any(s.get('client_name') == 'test_client_backend_testing' for s in status_list)
                        
                        if test_found:
                            self.log_test(
                                "Database CRUD Operations", 
                                True, 
                                "Operações de CREATE e READ funcionando corretamente"
                            )
                        else:
                            self.log_test(
                                "Database CRUD Operations", 
                                False, 
                                "Registro criado mas não encontrado na listagem",
                                None
                            )
                    else:
                        self.log_test(
                            "Database CRUD Operations", 
                            False, 
                            f"Erro ao ler dados do banco: {get_response.status_code}",
                            get_response.text
                        )
                else:
                    self.log_test(
                        "Database CRUD Operations", 
                        False, 
                        "Resposta de criação não contém campos esperados",
                        created_status
                    )
            else:
                self.log_test(
                    "Database CRUD Operations", 
                    False, 
                    f"Erro ao criar registro no banco: {response.status_code}",
                    response.text
                )
        except requests.exceptions.RequestException as e:
            self.log_test(
                "Database CRUD Operations", 
                False, 
                "Erro nas operações de banco de dados",
                str(e)
            )
    
    def run_all_tests(self):
        """Run all tests"""
        print("🚀 INICIANDO TESTES DO BACKEND DO BOT DE TRADING")
        print(f"Backend URL: {self.backend_url}")
        print(f"LM Studio URL: {self.lm_studio_url}")
        print("=" * 60)
        
        # Run all tests
        self.test_basic_connectivity()
        self.test_lm_studio_connectivity()
        self.test_trading_symbols_api()
        self.test_trading_analyze_api()
        self.test_trading_history_api()
        self.test_yahoo_finance_integration()
        self.test_technical_indicators()
        self.test_database_operations()
        
        # Summary
        print("\n" + "=" * 60)
        print("📊 RESUMO DOS TESTES")
        print("=" * 60)
        
        passed = sum(1 for result in self.test_results if result['success'])
        total = len(self.test_results)
        
        print(f"Total de testes: {total}")
        print(f"Testes aprovados: {passed}")
        print(f"Testes falharam: {total - passed}")
        print(f"Taxa de sucesso: {(passed/total)*100:.1f}%")
        
        print("\nDetalhes dos testes:")
        for result in self.test_results:
            status = "✅" if result['success'] else "❌"
            print(f"{status} {result['test']}: {result['message']}")
        
        return self.test_results

if __name__ == "__main__":
    tester = TradingBotTester()
    results = tester.run_all_tests()
    
    # Exit with error code if any tests failed
    failed_tests = [r for r in results if not r['success']]
    if failed_tests:
        print(f"\n⚠️  {len(failed_tests)} teste(s) falharam!")
        sys.exit(1)
    else:
        print("\n🎉 Todos os testes passaram!")
        sys.exit(0)