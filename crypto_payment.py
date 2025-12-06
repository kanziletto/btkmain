# crypto_payment.py
"""
USDT Ödeme Sistemi (TxID Doğrulamalı)
Kullanıcı TxID gönderir, bot TronScan'dan doğrular.
"""

import requests
from config import USDT_WALLET_ADDRESS, USDT_CONTRACT, SUBSCRIPTION_PLANS, PAYMENT_TOLERANCE

def get_payment_info(plan_key: str) -> dict:
    """Ödeme bilgilerini oluşturur."""
    plan = SUBSCRIPTION_PLANS.get(plan_key)
    if not plan:
        return None
    
    return {
        "wallet": USDT_WALLET_ADDRESS,
        "amount": plan["price"],
        "currency": "USDT (TRC20)",
        "plan": plan,
        "plan_key": plan_key
    }


def verify_txid(txid: str, expected_amount: float) -> dict:
    """
    TxID'yi TronScan API üzerinden doğrular.
    
    Args:
        txid: Transaction hash
        expected_amount: Beklenen tutar (dolar)
    
    Returns:
        dict: {
            "valid": bool,
            "error": str (if invalid),
            "amount": float,
            "to_address": str,
            "from_address": str
        }
    """
    try:
        # TronScan API'den transaction bilgisini al
        url = f"https://apilist.tronscanapi.com/api/transaction-info?hash={txid}"
        response = requests.get(url, timeout=30)
        data = response.json()
        
        # Transaction bulunamadı
        if not data or "contractRet" not in data:
            return {"valid": False, "error": "Transaction bulunamadı. TxID'yi kontrol edin."}
        
        # Transaction başarılı mı?
        if data.get("contractRet") != "SUCCESS":
            return {"valid": False, "error": f"Transaction başarısız: {data.get('contractRet')}"}
        
        # TRC20 transfer mi?
        trc20_info = data.get("trc20TransferInfo", [])
        
        if not trc20_info:
            # Belki tokenTransferInfo'da olabilir
            token_info = data.get("tokenTransferInfo", {})
            if token_info:
                to_address = token_info.get("to_address", "")
                amount_str = token_info.get("amount_str", "0")
                decimals = int(token_info.get("decimals", 6))
                amount = float(amount_str) / (10 ** decimals)
                from_address = token_info.get("from_address", "")
                contract = token_info.get("contract_address", "")
            else:
                return {"valid": False, "error": "Bu bir USDT (TRC20) transferi değil."}
        else:
            # TRC20 transfer bilgisi
            transfer = trc20_info[0]  # İlk transfer
            to_address = transfer.get("to_address", "")
            amount_str = transfer.get("amount_str", "0")
            decimals = int(transfer.get("decimals", 6))
            amount = float(amount_str) / (10 ** decimals)
            from_address = transfer.get("from_address", "")
            contract = transfer.get("contract_address", "")
        
        # USDT contract kontrolü
        if contract and contract != USDT_CONTRACT:
            return {"valid": False, "error": "Bu USDT değil, farklı bir token."}
        
        # Alıcı adres kontrolü
        if to_address.lower() != USDT_WALLET_ADDRESS.lower():
            return {
                "valid": False, 
                "error": f"Alıcı adresi uyuşmuyor.\nBeklenen: {USDT_WALLET_ADDRESS[:10]}...\nGelen: {to_address[:10]}..."
            }
        
        # Tutar kontrolü (tolerans ile)
        if abs(amount - expected_amount) > PAYMENT_TOLERANCE:
            return {
                "valid": False,
                "error": f"Tutar uyuşmuyor.\nBeklenen: ${expected_amount}\nGelen: ${amount}"
            }
        
        # Tüm kontroller geçti
        return {
            "valid": True,
            "amount": amount,
            "to_address": to_address,
            "from_address": from_address,
            "txid": txid
        }
        
    except requests.exceptions.Timeout:
        return {"valid": False, "error": "TronScan API zaman aşımı. Lütfen tekrar deneyin."}
    except Exception as e:
        return {"valid": False, "error": f"Doğrulama hatası: {str(e)}"}
