import asyncio
import os
import sys
from typing import Literal, Optional, Any

import httpx

from ccxt.async_support import okx
from ccxt.base.types import Position
from pydantic import BaseModel, Field

from logger import logger
from settings import settings

# 设置异步 ccxt okx 代理
os.environ['HTTP_PROXY'] = 'http://127.0.0.1:10808'
os.environ['HTTPS_PROXY'] = 'http://127.0.0.1:10808'

# ccxt okx 接口
exchange = okx({
    'options': {
        'defaultType': 'swap',  # OKX使用swap表示永续合约
    },
    'apiKey': settings.OKX_APIKEY,  # okx api key
    'secret': settings.OKX_SECRET,  # okx api 密钥
    'password': settings.OKX_PASSWORD,  # OKX需要交易密码
    'aiohttp_trust_env': True,  # 请求授信使用环境变量
})


# 初始化
async def setup_exchange(exchange: okx, leverage: int, symbol: str):
    """设置交易所参数"""
    try:
        # OKX设置杠杆
        await exchange.set_leverage(
            leverage,
            symbol,
            {'mgnMode': 'isolated'}  # 'cross'全仓模式，也可用'isolated'逐仓
        )

        # 设置持仓模式 (双向持仓)
        await exchange.set_position_mode(False, symbol)
    except:
        pass


# AI分析结构体
class SwapDirection(BaseModel):
    signal: Literal['buy', 'sell', 'hold'] = Field(..., description="买卖信号")
    reason: str = Field(..., description="分析理由")
    confidence: Literal['high', 'medium', 'low'] = Field(..., description="信心")
    trend: Literal['rising', 'falling', 'sideways', 'strong_rising', 'strong_falling'] = Field(..., description="趋势")


class Trade:
    def __init__(self, exchange: okx, symbol: str, leverage: int, usdt_amount: int, ai_endpoint: str, ai_api_key: str,
                 ai_base_url: str, ai_model: str):
        self._exchange = exchange
        self._symbol = symbol
        self._leverage = leverage
        self._usdt_amount = usdt_amount
        self._ai_endpoint = ai_endpoint
        self._ai_api_key = ai_api_key
        self._ai_base_url = ai_base_url
        self._ai_model = ai_model
        self._max_pnl: Optional[float] = None
        self._tag: str = "f1ee03b510d5SUDE"
        self._log_messages: list[str] = []

    # 日志
    def _log(self, msg: str):
        self._log_messages.append(msg)

    # 打印日志
    def _print_log(self):
        if len(self._log_messages) <= 0:
            return
        logger.info("\n" + "\n".join(self._log_messages))
        self._log_messages.clear()

    # 获取持仓列表
    async def get_position_list(self) -> list[Position]:
        res_positions = []
        positions = await self._exchange.fetch_positions()
        for pos in positions:
            contracts = float(pos['contracts']) if pos['contracts'] else 0
            if contracts > 0:
                res_positions.append(pos)

        return res_positions

    # 是否存在持仓
    @staticmethod
    def in_position(positions: list[Position], symbol: str) -> Optional[Position]:
        for pos in positions:
            if pos['symbol'] == symbol:
                return pos
        return None

    # USDT 换算张数
    async def usdt_to_contracts(self, symbol: str, usdt_amount: float, leverage: int) -> float:
        try:
            # 确保市场信息已加载
            await self._exchange.load_markets()
            market = self._exchange.markets.get(symbol)
            if market is None:
                raise RuntimeError(f"未找到市场信息: {symbol}")

            # 获取合约面值(contractSize)——若不存在则默认为1
            contract_size = None
            # ccxt 不同交易所/版本字段可能不同，尝试常见字段名
            for key in ("contractSize", "contract_size", "contractSize", "lotSize"):
                if key in market and market[key] is not None:
                    try:
                        contract_size = float(market[key])
                        break
                    except Exception:
                        continue
            if contract_size is None:
                # OKX 永续 USDT 合约通常以合约面值（如 0.001 BTC）计价；若无法获取则默认1
                contract_size = 1.0

            # 获取最新价格
            ticker = await self._exchange.fetch_ticker(symbol)
            price = float(ticker.get("last") or ticker.get("close") or 0)
            if price <= 0:
                raise RuntimeError("无法获取有效的最新价格用于换算")

            # 计算名义仓位（notional） = 实际投入 USDT * 杠杆
            notional = float(usdt_amount) * float(leverage)

            # 计算合约张数：contracts = notional / (price * contract_size)
            contracts = notional / (price * contract_size)

            # 对结果做合理的舍入，避免返回过多小数（交易所通常要求整数或有限小数）
            # 保留8位小数以兼容多数合约精度要求
            return round(contracts, 8)
        except Exception as e:
            raise RuntimeError(f"USDT 换算张数失败: {e}") from e

    # AI分析
    async def analyze(self) -> SwapDirection:
        async with httpx.AsyncClient(timeout=300) as client:
            try:
                response = await client.get(
                    url=f'{self._ai_endpoint}/api/v1/analyse/swap/okx',
                    params={
                        'symbol': self._symbol,
                        'leverage': self._leverage,
                        'timeframes': '1m,5m,15m,30m,1h,4h,1d',
                        'compare': 3
                    },
                    headers={
                        'OPENAI-API-KEY': self._ai_api_key,
                        'OPENAI-BASE-URL': self._ai_base_url,
                        'OPENAI-MODEL': self._ai_model,
                    }
                )
                response.raise_for_status()
                return SwapDirection.model_validate(response.json())
            except Exception as e:
                raise RuntimeError(f"AI分析接口 {self._symbol}: {e}") from e

    # 执行交易
    async def execute_deal(self) -> Optional[Any]:
        # 获取持仓
        position_list = await self.get_position_list()
        position = self.in_position(position_list, self._symbol)
        if position:
            return None

        # AI分析
        swap_direction = await self.analyze()
        if swap_direction.signal == 'hold':
            self._log(f"{self._symbol}: 观望中...")
            self._log(f"{self._symbol} AI分析结果: {swap_direction}")
            return None
        self._log(f"{self._symbol}: 开始交易...")
        self._log(f"{self._symbol} AI分析结果: {swap_direction}")

        # 交易
        if swap_direction.signal == 'buy':
            self._log(f"{self._symbol}: 开多仓...")
            res = await exchange.create_market_order(
                self._symbol,
                'buy',
                await self.usdt_to_contracts(self._symbol, self._usdt_amount, self._leverage),
                params={'tag': self._tag}
            )
            self._log(f"{self._symbol} 开多仓结果: {res}")
        elif swap_direction.signal == 'sell':
            self._log(f"{self._symbol}: 开空仓...")
            res = await exchange.create_market_order(
                self._symbol,
                'sell',
                await self.usdt_to_contracts(self._symbol, self._usdt_amount, self._leverage),
                params={'tag': self._tag}
            )
            self._log(f"{self._symbol} 开空仓结果: {res}")

        return None

    # 止损
    async def stop_loss(self, position: Position) -> Optional[Any]:
        contracts = float(position['contracts']) if position['contracts'] else 0
        side = position['side']
        if contracts == 0:
            return None
        if side == "long":
            self._log(f"平多止损...")
            await self._exchange.create_market_order(
                self._symbol,
                'sell',
                contracts,
                params={'reduceOnly': True, 'tag': self._tag}
            )
            return True
        if side == "short":
            self._log(f"平空止损...")
            await self._exchange.create_market_order(
                self._symbol,
                'buy',
                contracts,
                params={'tag': self._tag}
            )
            return True
        return False

    # 执行止损（-20%止损、盈利阶梯止盈）
    async def execute_stop_loss(self) -> Optional[Any]:
        # 获取持仓
        position_list = await self.get_position_list()
        position = self.in_position(position_list, self._symbol)
        if not position:
            return None

        initial_margin = float(position['initialMargin'])
        pnl = float(position['unrealizedPnl'])
        pnl_ratio = pnl / initial_margin
        self._max_pnl = pnl if self._max_pnl is None else max(self._max_pnl, pnl)
        max_pnl_ratio = self._max_pnl / initial_margin

        # 判断是否亏损20%以上
        if pnl_ratio <= -0.2:
            res = await self.stop_loss(position)
            self._max_pnl = None
            return res

        # 最高盈利 20% - 100% 之间
        elif max_pnl_ratio >= 0.2 and max_pnl_ratio < 1:
            if pnl <= self._max_pnl * 0.8:
                self._log("最高盈利 20% - 100% 之间, 回撤 20%, 平仓...")
                res = await self.stop_loss(position)
                self._max_pnl = None
                return res

        # 最高盈利 100% 以上
        elif max_pnl_ratio >= 1:
            if pnl <= self._max_pnl * 0.75:
                self._log("最高盈利 100% 以上, 回撤 25%, 平仓...")
                res = await self.stop_loss(position)
                self._max_pnl = None
                return res

    # 运行止损
    async def run_stop_loss(self, interval_second: int = 15):
        while True:
            try:
                await self.execute_stop_loss()
            except Exception as e:
                self._log(f"ERROR 运行止损 {self._symbol}: {e}")
            self._print_log()
            await asyncio.sleep(interval_second)

    # 运行交易
    async def run_deal(self, interval_minutes: int = 15):
        while True:
            try:
                await self.execute_deal()
            except Exception as e:
                self._log(f"ERROR 运行交易 {self._symbol}: {e}")
            self._print_log()
            await asyncio.sleep(60 * interval_minutes)

    # 运行
    async def run(self):
        await asyncio.gather(
            self.run_deal(settings.INTERVAL_MINUTES),
            self.run_stop_loss(15),
        )


# 同时做这些币
tracking_symbols: list[str] = [
    'BTC/USDT:USDT',
    'ETH/USDT:USDT',
    'BNB/USDT:USDT',
    'SOL/USDT:USDT',
    'DOGE/USDT:USDT',
    'XRP/USDT:USDT',
]

if __name__ == '__main__':
    if settings.INTERVAL_MINUTES <= 0:
        sys.exit("INTERVAL_MINUTES 必须大于 0")
    elif settings.USDT_AMOUNT < 1:
        sys.exit("USDT_AMOUNT 必须大于等于 1")
    elif settings.LEVERAGE < 1:
        sys.exit("LEVERAGE 必须大于等于 1")

    trades: list[Trade] = []
    for symbol in tracking_symbols:
        trades.append(Trade(exchange, symbol, settings.LEVERAGE, settings.USDT_AMOUNT, settings.AI_ENDPOINT,
                            settings.OPENAI_API_KEY, settings.OPENAI_BASE_URL, settings.OPENAI_MODEL))


    async def main():
        # 初始化
        for symbol in tracking_symbols:
            await setup_exchange(exchange, settings.LEVERAGE, symbol)

        tasks = [trade.run() for trade in trades]
        await asyncio.gather(*tasks)


    asyncio.run(main())
