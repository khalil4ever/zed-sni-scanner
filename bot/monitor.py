import asyncio

from scanner.tester import test_hostname
from database.database import (
    get_monitored_hosts,
    update_monitored_host,
    save_result,
)


CHECK_INTERVAL = 300  # 5 minutes


async def monitor_hosts(bot=None, channel_id=None):

    while True:

        try:

            hosts = get_monitored_hosts()

            for row in hosts:

                (
                    host_id,
                    hostname,
                    network,
                    enabled,
                    previous_status,
                    previous_latency,
                    last_checked,
                ) = row

                if not enabled:
                    continue

                try:

                    result = await test_hostname(hostname)

                    current_status = result["status"]

                    latency = result["latency_ms"]

                    if not isinstance(latency, int):
                        latency = None

                    # Save monitoring result.
                    save_result(
                        hostname=result["hostname"],
                        status=current_status,
                        dns=result["dns"],
                        tcp=result["tcp"],
                        tls=result["tls"],
                        https=result["https"],
                        latency_ms=latency,
                        network=network,
                    )

                    old_status = update_monitored_host(
                        hostname=hostname,
                        status=current_status,
                        latency_ms=latency,
                    )

                    # Notify only when the status changes.
                    if (
                        bot is not None
                        and channel_id is not None
                        and old_status is not None
                        and old_status != current_status
                    ):

                        if current_status == "ACTIVE":

                            message = (
                                "🟢 <b>HOSTNAME RESTORED</b>\n\n"
                                f"🌐 <code>{hostname}</code>\n"
                                f"Network: {network or 'General'}\n\n"
                                f"Status: 🟢 ACTIVE\n"
                                f"Latency: {latency or 'N/A'} ms"
                            )

                        elif (
                            current_status == "DEAD"
                            and old_status == "ACTIVE"
                        ):

                            message = (
                                "🚨 <b>HOSTNAME DOWN</b>\n\n"
                                f"🌐 <code>{hostname}</code>\n"
                                f"Network: {network or 'General'}\n\n"
                                "Previous: 🟢 ACTIVE\n"
                                "Current: 🔴 DEAD"
                            )

                        else:

                            message = (
                                "🔄 <b>HOSTNAME STATUS CHANGED</b>\n\n"
                                f"🌐 <code>{hostname}</code>\n"
                                f"Network: {network or 'General'}\n\n"
                                f"Previous: {old_status}\n"
                                f"Current: {current_status}"
                            )

                        try:

                            await bot.send_message(
                                chat_id=channel_id,
                                text=message,
                                parse_mode="HTML",
                            )

                        except Exception as notification_error:

                            print(
                                "Notification error:",
                                notification_error,
                            )

                except Exception as test_error:

                    print(
                        f"Monitor test error for "
                        f"{hostname}: {test_error}"
                    )

        except Exception as monitor_error:

            print(
                "Monitoring loop error:",
                monitor_error,
            )

        await asyncio.sleep(CHECK_INTERVAL)
