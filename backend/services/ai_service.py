"""AI assistant service — tool definitions, executor, config management."""

import json
import logging
import os
from datetime import datetime, timezone

from backend.models import Account, Conversation, Holding, WatchlistItem

logger = logging.getLogger(__name__)

# ── System Prompt ──────────────────────────────────────────────

SYSTEM_PROMPT = """你是"墨账"（EasyFund）的 AI 资产助手。你帮助用户管理家庭资产，回答关于账户、持仓、汇率、交易等财务问题。

你可以：
- 查询用户的资产数据（账户余额、持仓、盈亏、汇率等）
- 执行安全操作（添加/移除关注列表、刷新价格、更新汇率）
- 回答金融理财相关的知识问题

规则：
- 始终用中文回复
- 金额显示时标注币种
- 涉及具体数据时，调用工具获取最新数据，不要凭记忆回答
- 不提供具体的投资建议，只提供数据和分析
- 执行操作前确认用户意图"""

# ── Tool Definitions (OpenAI function calling format) ──────────

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_dashboard_overview",
            "description": "获取资产总览，包括总资产（CNY）、分类占比、汇率、账户数量和持仓数量",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_asset_trend",
            "description": "获取资产历史趋势数据",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_accounts",
            "description": "列出所有账户，可按类别筛选（cash=现金, investment=投资, insurance=保险, future_cash=公积金/社保）",
            "parameters": {
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "description": "账户类别筛选，可选：cash, investment, insurance, future_cash。不传则返回全部",
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_account",
            "description": "获取单个账户的详细信息，包括余额、保险细节等",
            "parameters": {
                "type": "object",
                "properties": {
                    "account_id": {"type": "string", "description": "账户ID"},
                },
                "required": ["account_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_holdings",
            "description": "列出所有股票持仓",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_holding_pnl",
            "description": "获取某个持仓的盈亏详情",
            "parameters": {
                "type": "object",
                "properties": {
                    "holding_id": {"type": "string", "description": "持仓ID"},
                },
                "required": ["holding_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_stock_quote",
            "description": "获取股票实时报价，包含当前价格、前收盘价、涨跌幅",
            "parameters": {
                "type": "object",
                "properties": {
                    "ticker": {"type": "string", "description": "股票代码，如 BIDU, NVDA, 9988.HK"},
                },
                "required": ["ticker"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_transactions",
            "description": "列出交易记录，可按账户ID和年份筛选",
            "parameters": {
                "type": "object",
                "properties": {
                    "account_id": {"type": "string", "description": "按账户ID筛选"},
                    "year": {"type": "integer", "description": "按年份筛选"},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_annual_pnl",
            "description": "获取年度盈亏汇总，按账户和年份分组",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_fund_flow_analysis",
            "description": "获取投资账户的资金流分析，包括入金/出金总额、汇兑损益、投资收益分解",
            "parameters": {
                "type": "object",
                "properties": {
                    "account_id": {"type": "string", "description": "投资账户ID"},
                },
                "required": ["account_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_exchange_rates",
            "description": "获取当前汇率（USD/CNY, HKD/CNY 等）",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_stock_tracker_overview",
            "description": "获取股价追踪概览，包括持仓和关注列表的股票、涨跌幅、盈亏",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_watchlist",
            "description": "列出股票关注列表",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "add_watchlist_item",
            "description": "添加股票到关注列表",
            "parameters": {
                "type": "object",
                "properties": {
                    "id": {"type": "string", "description": "关注项ID（如 ticker 小写）"},
                    "ticker": {"type": "string", "description": "股票代码"},
                    "name": {"type": "string", "description": "股票名称"},
                },
                "required": ["id", "ticker"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "remove_watchlist_item",
            "description": "从关注列表移除股票",
            "parameters": {
                "type": "object",
                "properties": {
                    "item_id": {"type": "string", "description": "关注项ID"},
                },
                "required": ["item_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "refresh_stock_prices",
            "description": "刷新所有持仓的股票价格（从 yfinance 获取最新价）",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "refresh_exchange_rates",
            "description": "刷新汇率（从 yfinance/frankfurter 获取最新汇率）",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_exchange_rate",
            "description": "手动更新单个汇率",
            "parameters": {
                "type": "object",
                "properties": {
                    "currency": {"type": "string", "description": "币种，如 USD, HKD"},
                    "rate": {"type": "number", "description": "对人民币汇率"},
                },
                "required": ["currency", "rate"],
            },
        },
    },
]


# ── Tool Executor ──────────────────────────────────────────────

async def execute_tool(name: str, args: dict) -> dict:
    """Execute a tool by name, calling existing ORM methods."""
    if name == "get_dashboard_overview":
        from backend.routers.dashboard import overview
        return await overview()

    elif name == "get_asset_trend":
        from backend.routers.dashboard import trend
        return await trend()

    elif name == "list_accounts":
        qs = Account.all()
        category = args.get("category")
        if category:
            qs = qs.filter(category=category)
        accounts = await qs
        result = [a.to_dict() for a in accounts]
        return {"accounts": result, "count": len(result)}

    elif name == "get_account":
        account = await Account.get_or_none(id=args["account_id"])
        if not account:
            return {"error": "账户未找到"}
        return account.to_dict()

    elif name == "list_holdings":
        holdings = await Holding.all()
        result = [h.to_dict() for h in holdings]
        return {"holdings": result, "count": len(result)}

    elif name == "get_holding_pnl":
        item = await Holding.get_or_none(id=args["holding_id"])
        if not item:
            return {"error": "持仓未找到"}
        cost = item.shares * item.avg_cost_price
        market = item.shares * item.current_price
        pnl = market - cost
        pnl_pct = (pnl / cost * 100) if cost else 0
        return {
            "id": args["holding_id"],
            "ticker": item.ticker,
            "shares": item.shares,
            "cost": round(cost, 2),
            "market_value": round(market, 2),
            "pnl": round(pnl, 2),
            "pnl_pct": round(pnl_pct, 2),
            "currency": item.currency,
        }

    elif name == "get_stock_quote":
        from backend.services.market import get_quote
        return get_quote(args["ticker"])

    elif name == "list_transactions":
        from backend.models import Transaction
        qs = Transaction.all()
        account_id = args.get("account_id")
        year = args.get("year")
        if account_id:
            qs = qs.filter(account_id=account_id)
        if year:
            qs = qs.filter(date__startswith=str(year))
        items = await qs
        result = [t.to_dict() for t in items]
        return {"transactions": result, "count": len(result)}

    elif name == "get_annual_pnl":
        from backend.routers.transactions import annual_pnl
        return await annual_pnl()

    elif name == "get_fund_flow_analysis":
        from backend.routers.fund_flows import fund_flow_analysis
        return await fund_flow_analysis(account_id=args["account_id"])

    elif name == "get_exchange_rates":
        from backend.services.currency import get_all_rates
        rates = await get_all_rates()
        return {"rates": {c: r for c, r in rates.items()}}

    elif name == "get_stock_tracker_overview":
        from backend.routers.stock_tracker import tracker_overview
        return await tracker_overview()

    elif name == "list_watchlist":
        items = await WatchlistItem.all()
        return [w.to_dict() for w in items]

    elif name == "add_watchlist_item":
        item_data = {"id": args["id"], "ticker": args["ticker"], "name": args.get("name", "")}
        existing = await WatchlistItem.get_or_none(id=item_data["id"])
        if existing:
            return {"error": f"关注列表中已存在 {args['ticker']}"}
        item = await WatchlistItem.create(**item_data)
        return item.to_dict()

    elif name == "remove_watchlist_item":
        item = await WatchlistItem.get_or_none(id=args["item_id"])
        if not item:
            return {"error": "关注项未找到"}
        await item.delete()
        return {"ok": True}

    elif name == "refresh_stock_prices":
        from backend.routers.investments import refresh_prices
        return await refresh_prices()

    elif name == "refresh_exchange_rates":
        from backend.services.currency import refresh_rates_from_yfinance
        from backend.services.market import _rate_cache
        _rate_cache.clear()
        rates = await refresh_rates_from_yfinance()
        return {"rates": rates}

    elif name == "update_exchange_rate":
        from backend.services.currency import update_rate
        await update_rate(args["currency"], args["rate"])
        return {"ok": True, "currency": args["currency"], "rate": args["rate"]}

    else:
        return {"error": f"未知工具: {name}"}


# ── AI Config Helpers ──────────────────────────────────────────

def load_ai_config() -> dict:
    """Load AI config from environment variables only."""
    return {
        "base_url": os.environ.get("EASYFUND_AI_BASE_URL", "https://api.openai.com/v1"),
        "api_key": os.environ.get("EASYFUND_AI_API_KEY", ""),
        "model": os.environ.get("EASYFUND_AI_MODEL", "gpt-4o-mini"),
    }


def mask_api_key(config: dict) -> dict:
    """Return config with API key masked for frontend display."""
    masked = {**config}
    key = masked.get("api_key", "")
    if key and len(key) > 8:
        masked["api_key"] = key[:4] + "..." + key[-4:]
    elif key:
        masked["api_key"] = "****"
    return masked


# ── Streaming Chat ─────────────────────────────────────────────

import httpx
import uuid

MAX_TOOL_ROUNDS = 5


async def stream_chat(
    messages: list[dict],
):
    """Stream a chat completion with tool calling support.

    Yields SSE event strings: "event: ...\ndata: ...\n\n"
    """
    config = load_ai_config()
    base_url = config.get("base_url", "").rstrip("/")
    api_key = config.get("api_key", "")
    model = config.get("model", "gpt-4o-mini")

    if not api_key:
        yield _sse("error", {"detail": "AI 未配置，请先在设置中填写 API Key"})
        return

    url = f"{base_url}/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    # Build the message list with system prompt
    api_messages = [{"role": "system", "content": SYSTEM_PROMPT}] + messages

    for round_num in range(MAX_TOOL_ROUNDS):
        body = {
            "model": model,
            "messages": api_messages,
            "tools": TOOLS,
            "stream": True,
        }

        # Collect full response for tool calling
        tool_calls_map: dict[int, dict] = {}  # index -> {id, name, arguments}
        content_parts: list[str] = []
        finish_reason = None

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                async with client.stream("POST", url, json=body, headers=headers) as resp:
                    if resp.status_code != 200:
                        error_text = await resp.aread()
                        try:
                            error_data = json.loads(error_text)
                            detail = error_data.get("error", {}).get("message", error_text.decode())
                        except Exception:
                            detail = error_text.decode()[:200]
                        yield _sse("error", {"detail": f"AI API 错误: {detail}"})
                        return

                    async for line in resp.aiter_lines():
                        if not line.startswith("data: "):
                            continue
                        data_str = line[6:]
                        if data_str.strip() == "[DONE]":
                            break

                        try:
                            chunk = json.loads(data_str)
                        except json.JSONDecodeError:
                            continue

                        choice = chunk.get("choices", [{}])[0]
                        delta = choice.get("delta", {})
                        finish_reason = choice.get("finish_reason")

                        # Handle content
                        content = delta.get("content")
                        if content:
                            content_parts.append(content)
                            yield _sse("content", {"text": content})

                        # Handle tool calls (streaming accumulation)
                        tc_list = delta.get("tool_calls")
                        if tc_list:
                            for tc in tc_list:
                                idx = tc.get("index", 0)
                                if idx not in tool_calls_map:
                                    tool_calls_map[idx] = {"id": "", "name": "", "arguments": ""}
                                if tc.get("id"):
                                    tool_calls_map[idx]["id"] = tc["id"]
                                if tc.get("function", {}).get("name"):
                                    tool_calls_map[idx]["name"] = tc["function"]["name"]
                                if tc.get("function", {}).get("arguments"):
                                    tool_calls_map[idx]["arguments"] += tc["function"]["arguments"]

        except httpx.ConnectError:
            yield _sse("error", {"detail": "AI API 连接失败，请检查网络或 API 地址配置"})
            return
        except httpx.TimeoutException:
            yield _sse("error", {"detail": "AI API 请求超时，请稍后重试"})
            return
        except Exception as e:
            logger.exception("Stream chat error")
            yield _sse("error", {"detail": f"AI API 错误: {str(e)}"})
            return

        # If no tool calls, we're done
        if not tool_calls_map or finish_reason != "tool_calls":
            break

        # Execute tool calls
        assistant_msg = {
            "role": "assistant",
            "content": "".join(content_parts) or None,
            "tool_calls": [],
        }
        tool_results = []

        for idx in sorted(tool_calls_map.keys()):
            tc = tool_calls_map[idx]
            tool_name = tc["name"]
            tool_id = tc["id"]

            try:
                tool_args = json.loads(tc["arguments"]) if tc["arguments"] else {}
            except json.JSONDecodeError:
                tool_args = {}

            # Notify frontend about tool call
            yield _sse("tool_call", {"name": tool_name, "args": tool_args, "status": "calling", "id": tool_id, "arguments": tc["arguments"]})

            # Execute the tool
            try:
                result = await execute_tool(tool_name, tool_args)
            except Exception as e:
                logger.exception("Tool execution error: %s(%s)", tool_name, tool_args)
                result = {"error": f"工具执行失败: {str(e)}"}

            yield _sse("tool_result", {"name": tool_name, "id": tool_id, "result": result})

            assistant_msg["tool_calls"].append({
                "id": tool_id,
                "type": "function",
                "function": {"name": tool_name, "arguments": tc["arguments"]},
            })

            tool_results.append({
                "role": "tool",
                "tool_call_id": tool_id,
                "content": json.dumps(result, ensure_ascii=False, default=str),
            })

        # Add assistant message and tool results to conversation for next round
        api_messages.append(assistant_msg)
        api_messages.extend(tool_results)

    yield _sse("done", {})


def _sse(event: str, data: dict) -> str:
    """Format an SSE event string."""
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False, default=str)}\n\n"
