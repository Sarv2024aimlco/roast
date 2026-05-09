import time
import asyncio
import structlog

logger = structlog.get_logger()


class CircuitBreaker:
    """
    Three states:
    - closed:    normal operation, requests go through
    - open:      provider failed 3+ times, skip it entirely
    - half_open: cooldown passed, allow one probe request
    """

    def __init__(self, name: str, failure_threshold: int = 3, cooldown_seconds: int = 300):
        self.name = name
        self.failure_threshold = failure_threshold
        self.cooldown_seconds = cooldown_seconds
        self.failures = 0
        self.last_failure_time: float | None = None
        self.state = "closed"

    def record_failure(self) -> None:
        self.failures += 1
        self.last_failure_time = time.time()
        if self.failures >= self.failure_threshold:
            self.state = "open"
            logger.warning("circuit_opened", provider=self.name, failures=self.failures)

    def record_success(self) -> None:
        if self.state == "half_open":
            self.state = "closed"
            self.failures = 0
            logger.info("circuit_closed", provider=self.name)

    def should_skip(self) -> bool:
        if self.state == "open":
            if self.last_failure_time and time.time() - self.last_failure_time > self.cooldown_seconds:
                self.state = "half_open"
                logger.info("circuit_half_open", provider=self.name)
                return False  # allow one probe
            return True
        return False


# One circuit breaker per provider — module-level singletons
groq_circuit = CircuitBreaker(name="groq")
gemini_circuit = CircuitBreaker(name="gemini")
cerebras_circuit = CircuitBreaker(name="cerebras")
openrouter_circuit = CircuitBreaker(name="openrouter")
nim_circuit = CircuitBreaker(name="nvidia_nim")
