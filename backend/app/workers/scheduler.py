import random
from datetime import datetime
from typing import List, Dict, Any

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from loguru import logger

from app.workers.telegram_worker import run_send_job


class CampaignScheduler:
    """
    High-level campaign scheduler.
    """

    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.scheduler.start()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def schedule_campaign(
        self,
        *,
        campaign_id: str,
        interval_minutes: int,
        campaign_payload: Dict[str, Any],
    ):
        """
        Schedule a campaign to run at a fixed interval.
        """

        logger.info(
            f"Scheduling campaign [{campaign_id}] every {interval_minutes} min"
        )

        self.scheduler.add_job(
            self._run_campaign,
            trigger=IntervalTrigger(minutes=interval_minutes),
            kwargs={
                "campaign_id": campaign_id,
                "payload": campaign_payload,
            },
            id=f"campaign_{campaign_id}",
            replace_existing=True,
        )

    def remove_campaign(self, campaign_id: str):
        job_id = f"campaign_{campaign_id}"
        try:
            self.scheduler.remove_job(job_id)
            logger.info(f"Removed campaign [{campaign_id}]")
        except Exception:
            logger.warning(f"Campaign [{campaign_id}] not found")

    # ------------------------------------------------------------------
    # Core execution
    # ------------------------------------------------------------------

    async def _run_campaign(self, campaign_id: str, payload: Dict[str, Any]):
        """
        Runs one campaign cycle.
        """
        logger.info(f"Running campaign [{campaign_id}]")

        accounts = payload["accounts"]
        targets = payload["targets"]
        message = payload["message"]
        account_type = payload["account_type"]

        jobs = self._build_jobs(
            accounts=accounts,
            targets=targets,
            message=message,
            account_type=account_type,
        )

        for job in jobs:
            logger.debug(
                f"Dispatching job | acct={job['account_id']} | tgt={job['target']}"
            )

            # In production this would be Celery.delay(...)
            run_send_job(job)

    # ------------------------------------------------------------------
    # Job builder
    # ------------------------------------------------------------------

    def _build_jobs(
        self,
        *,
        accounts: List[Dict[str, Any]],
        targets: List[str],
        message: str,
        account_type: str,
    ) -> List[Dict[str, Any]]:
        """
        Creates send jobs by pairing accounts and targets.
        """

        jobs = []

        shuffled_targets = targets[:]
        random.shuffle(shuffled_targets)

        for account in accounts:
            if not shuffled_targets:
                break

            target = shuffled_targets.pop()

            jobs.append(
                {
                    "account_id": account["id"],
                    "session_name": account["session_name"],
                    "api_id": account["api_id"],
                    "api_hash": account["api_hash"],
                    "target": target,
                    "message": message,
                    "account_type": account_type,
                    "created_at": datetime.utcnow().isoformat(),
                }
            )

        return jobs
