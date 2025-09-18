#!/usr/bin/env python3
import asyncio
import time
from typing import Dict, Any, List

# Import the consumer if available; otherwise define a minimal inline version
try:
	from src.monitoring.smart_money_consumer import SmartMoneyAlertConsumer  # type: ignore
except Exception:
	class SmartMoneyAlertConsumer:  # minimal inline
		def __init__(self, detector, alert_manager):
			self.detector = detector
			self.alert_manager = alert_manager
		async def process_symbol(self, symbol: str, market_data: Dict[str, Any]) -> None:
			events = await self.detector.analyze_market_data(symbol, market_data)
			for ev in events:
				if not self.detector.should_send_alert(symbol, ev):
					continue
				content = {
					'type': 'SMART_MONEY',
					'symbol': symbol,
					'sophistication': getattr(ev, 'sophistication_level', type('L',(),{'value':'HIGH'})).value,
					'score': getattr(ev, 'sophistication_score', 0),
					'confidence': getattr(ev, 'confidence', 0),
					'details': getattr(ev, 'data', {})
				}
				await self.alert_manager.send_alert('smart_money', content)
				self.detector.record_alert_sent(symbol, ev)


class StubAlertManager:
	def __init__(self):
		self.sent: List[Dict[str, Any]] = []
	async def send_alert(self, channel: str, content: Dict[str, Any]) -> None:
		self.sent.append({'channel': channel, 'content': content, 'ts': time.time()})


class FakeEvent:
	def __init__(self, sophistication_score: float, confidence: float, data: Dict[str, Any]):
		self.sophistication_level = type('Level', (), {'value': 'HIGH'})
		self.sophistication_score = sophistication_score
		self.confidence = confidence
		self.data = data
		self.event_type = type('E', (), {'value': 'LARGE_AGG_BUY'})


class StubDetector:
	def __init__(self, score_threshold: float = 7.0, confidence_threshold: float = 0.7, cooldown_minutes: float = 1.0):
		self.score_threshold = score_threshold
		self.confidence_threshold = confidence_threshold
		self.cooldown_minutes = cooldown_minutes
		self._sent = {}
		self._last_sent_ts = {}
	async def analyze_market_data(self, symbol: str, market_data: Dict[str, Any]):
		# Create a fake event when thresholds exceeded
		score = market_data.get('smart_money_score', 0)
		conf = market_data.get('confidence', 0)
		if score >= self.score_threshold and conf >= self.confidence_threshold:
			return [FakeEvent(score, conf, {'notional': market_data.get('notional', 0)})]
		return []
	def should_send_alert(self, symbol: str, ev: FakeEvent) -> bool:
		# Cooldown-based deduplication
		now = time.time()
		last_ts = self._last_sent_ts.get(symbol)
		if last_ts is not None and (now - last_ts) < (self.cooldown_minutes * 60):
			return False
		# Per-minute duplicate guard as backstop
		key = (symbol, int(now//60))
		if key in self._sent:
			return False
		return ev.sophistication_score >= self.score_threshold and ev.confidence >= self.confidence_threshold
	def record_alert_sent(self, symbol: str, ev: FakeEvent) -> None:
		now = time.time()
		key = (symbol, int(now//60))
		self._sent[key] = True
		self._last_sent_ts[symbol] = now


async def main():
	alert_mgr = StubAlertManager()
	detector = StubDetector(score_threshold=7.0, confidence_threshold=0.75, cooldown_minutes=1.0)
	consumer = SmartMoneyAlertConsumer(detector, alert_mgr)
	# Sample market data (above thresholds)
	above = {
		'last': 61000.0,
		'volume': 1234.5,
		'notional': 4_000_000,
		'smart_money_score': 8.2,
		'confidence': 0.81,
	}
	# Case 1: Above thresholds -> should alert
	await consumer.process_symbol('BTCUSDT', above)
	count_after_first = len(alert_mgr.sent)
	# Case 2: Below thresholds -> should not alert
	below = {
		'last': 61000.0,
		'volume': 500.0,
		'notional': 200_000,
		'smart_money_score': 6.2,
		'confidence': 0.62,
	}
	await consumer.process_symbol('ETHUSDT', below)
	count_after_below = len(alert_mgr.sent)
	# Case 3: Duplicate within cooldown -> suppressed
	await consumer.process_symbol('BTCUSDT', above)
	count_after_dup_cooldown = len(alert_mgr.sent)
	# Case 4: After cooldown expiry -> allow another alert
	# Force cooldown to expire by backdating both last_ts and minute guard key
	old_minute_key = ('BTCUSDT', int(time.time()//60))
	if old_minute_key in detector._sent:
		del detector._sent[old_minute_key]
	detector._last_sent_ts['BTCUSDT'] = time.time() - (detector.cooldown_minutes * 60 + 5)
	await consumer.process_symbol('BTCUSDT', above)
	count_after_cooldown = len(alert_mgr.sent)
	# Print concise JSON result for CI-like parsing
	import json
	print(json.dumps({
		'counts': {
			'after_first': count_after_first,
			'after_below': count_after_below,
			'after_duplicate_within_cooldown': count_after_dup_cooldown,
			'after_cooldown_expired': count_after_cooldown
		},
		'below_threshold_dropped': count_after_below == count_after_first,
		'suppression_worked': count_after_dup_cooldown == count_after_first,
		'cooldown_release_worked': count_after_cooldown == (count_after_first + 1),
		'alerts_preview': alert_mgr.sent[:2]
	}, default=str))


if __name__ == '__main__':
	asyncio.run(main())
