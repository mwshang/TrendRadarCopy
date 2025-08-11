import os
import yaml
from pathlib import Path


def load_config():
    config_path = os.environ.get("CONFIG_PATH", "config/config.yaml")

    if not Path(config_path).exists():
        raise FileNotFoundError(f"配置文件 {config_path} 不存在")

    with open(config_path, "r", encoding="utf-8") as f:
        config_data = yaml.safe_load(f)

    print(f"配置文件加载成功: {config_path}")

    # 检查模式
    mode = config_data["platforms"].get("mode", "realtime")
    if mode not in ["realtime", "hot"]:
        raise ValueError(f"无效的模式: {mode}")

    # 获取所有数据源
    data_sources = list(config_data["platforms"].keys())
    data_sources.remove("mode")  # 移除模式字段

    # 合并所有平台的配置
    all_platforms = []
    source_headers = {}

    for source in data_sources:
        if source not in config_data["platforms"]:
            continue

        source_config = config_data["platforms"][source]

        # 获取当前模式的平台列表
        platforms_list = source_config.get(mode, [])

        # 获取当前模式的请求头
        headers_key = f"{mode}_headers"
        headers = source_config.get(headers_key, {})
        source_headers[source] = headers

        # 为每个平台添加数据源类型
        for platform in platforms_list:
            platform["source"] = source
            all_platforms.append(platform)

    # 构建配置
    config = {
        "VERSION_CHECK_URL": config_data["app"]["version_check_url"],
        "SHOW_VERSION_UPDATE": config_data["app"]["show_version_update"],
        "REQUEST_INTERVAL": config_data["crawler"]["request_interval"],
        "REQUEST_MIN_INTERVAL": config_data["crawler"]["request_min_interval"],
        "REQUEST_MAX_INTERVAL": config_data["crawler"]["request_max_interval"],
        "RECENT_DAYS": config_data["crawler"]["recent_days"],
        "REPORT_MODE": config_data["report"]["mode"],
        "RANK_THRESHOLD": config_data["report"]["rank_threshold"],
        "USE_PROXY": config_data["crawler"]["use_proxy"],
        "DEFAULT_PROXY": config_data["crawler"]["default_proxy"],
        "ENABLE_CRAWLER": config_data["crawler"]["enable_crawler"],
        "ENABLE_NOTIFICATION": config_data["notification"]["enable_notification"],
        "MESSAGE_BATCH_SIZE": config_data["notification"]["message_batch_size"],
        "BATCH_SEND_INTERVAL": config_data["notification"]["batch_send_interval"],
        "FEISHU_MESSAGE_SEPARATOR": config_data["notification"][
            "feishu_message_separator"
        ],
        "WEIGHT_CONFIG": {
            "RANK_WEIGHT": config_data["weight"]["rank_weight"],
            "FREQUENCY_WEIGHT": config_data["weight"]["frequency_weight"],
            "HOTNESS_WEIGHT": config_data["weight"]["hotness_weight"],
        },
        "PLATFORMS": all_platforms,
        "SOURCE_HEADERS": source_headers,
    }

    # Webhook配置（环境变量优先）
    notification = config_data.get("notification", {})
    webhooks = notification.get("webhooks", {})

    config["FEISHU_WEBHOOK_URL"] = os.environ.get(
        "FEISHU_WEBHOOK_URL", ""
    ).strip() or webhooks.get("feishu_url", "")
    config["DINGTALK_WEBHOOK_URL"] = os.environ.get(
        "DINGTALK_WEBHOOK_URL", ""
    ).strip() or webhooks.get("dingtalk_url", "")
    config["WEWORK_WEBHOOK_URL"] = os.environ.get(
        "WEWORK_WEBHOOK_URL", ""
    ).strip() or webhooks.get("wework_url", "")
    config["TELEGRAM_BOT_TOKEN"] = os.environ.get(
        "TELEGRAM_BOT_TOKEN", ""
    ).strip() or webhooks.get("telegram_bot_token", "")
    config["TELEGRAM_CHAT_ID"] = os.environ.get(
        "TELEGRAM_CHAT_ID", ""
    ).strip() or webhooks.get("telegram_chat_id", "")

    # 输出配置来源信息
    webhook_sources = []
    if config["FEISHU_WEBHOOK_URL"]:
        source = "环境变量" if os.environ.get("FEISHU_WEBHOOK_URL") else "配置文件"
        webhook_sources.append(f"飞书({source})")
    if config["DINGTALK_WEBHOOK_URL"]:
        source = "环境变量" if os.environ.get("DINGTALK_WEBHOOK_URL") else "配置文件"
        webhook_sources.append(f"钉钉({source})")
    if config["WEWORK_WEBHOOK_URL"]:
        source = "环境变量" if os.environ.get("WEWORK_WEBHOOK_URL") else "配置文件"
        webhook_sources.append(f"企业微信({source})")
    if config["TELEGRAM_BOT_TOKEN"] and config["TELEGRAM_CHAT_ID"]:
        token_source = (
            "环境变量" if os.environ.get("TELEGRAM_BOT_TOKEN") else "配置文件"
        )
        chat_source = "环境变量" if os.environ.get("TELEGRAM_CHAT_ID") else "配置文件"
        webhook_sources.append(f"Telegram({token_source}/{chat_source})")

    if webhook_sources:
        print(f"Webhook 配置来源: {', '.join(webhook_sources)}")
    else:
        print("未配置任何 Webhook")

    return config


# 全局配置变量
print("正在加载配置...")
CONFIG = load_config()
print(f"监控平台数量: {len(CONFIG['PLATFORMS'])}")