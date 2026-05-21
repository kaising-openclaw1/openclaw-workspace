"""连接质量监控 - 实时测量延迟、带宽、帧率"""
import logging
import time
from typing import Optional

logger = logging.getLogger(__name__)


class QualityMonitor:
    """连接质量监控器
    
    实时测量并报告连接质量指标：
    - 延迟 (RTT)
    - 帧率 (FPS)
    - 带宽利用率
    - 丢包率
    - 综合质量评分 (0-100)
    """
    
    def __init__(self, window_size: int = 30):
        self.window_size = window_size
        self._latencies = []
        self._frame_times = []
        self._bytes_sent = 0
        self._bytes_received = 0
        self._frames_sent = 0
        self._frames_dropped = 0
        self._last_bandwidth_check = time.time()
        self._bandwidth = 0.0  # Mbps
        self._start_time = time.time()
    
    def record_latency(self, rtt_ms: float):
        """记录一次延迟测量"""
        self._latencies.append(rtt_ms)
        if len(self._latencies) > self.window_size:
            self._latencies.pop(0)
    
    def record_frame(self, frame_size_bytes: int, dropped: bool = False):
        """记录一帧"""
        self._frame_times.append(time.time())
        self._frames_sent += 1
        self._bytes_sent += frame_size_bytes
        
        if dropped:
            self._frames_dropped += 1
        
        # 保留最近 30 秒的数据
        cutoff = time.time() - 30
        while self._frame_times and self._frame_times[0] < cutoff:
            self._frame_times.pop(0)
    
    def record_bytes_received(self, n: int):
        self._bytes_received += n
    
    def get_fps(self) -> float:
        """当前帧率"""
        if len(self._frame_times) < 2:
            return 0.0
        now = time.time()
        cutoff = now - 1.0
        recent = [t for t in self._frame_times if t >= cutoff]
        return len(recent)
    
    def get_avg_latency(self) -> float:
        """平均延迟 (ms)"""
        if not self._latencies:
            return 0.0
        return sum(self._latencies) / len(self._latencies)
    
    def get_p95_latency(self) -> float:
        """P95 延迟"""
        if not self._latencies:
            return 0.0
        sorted_latencies = sorted(self._latencies)
        idx = int(len(sorted_latencies) * 0.95)
        return sorted_latencies[min(idx, len(sorted_latencies) - 1)]
    
    def get_bandwidth(self) -> float:
        """当前带宽 (Mbps)"""
        now = time.time()
        elapsed = now - self._last_bandwidth_check
        
        if elapsed < 1.0:
            return self._bandwidth
        
        self._bandwidth = (self._bytes_sent * 8) / (elapsed * 1_000_000)  # Mbps
        self._bytes_sent = 0
        self._last_bandwidth_check = now
        return self._bandwidth
    
    def get_packet_loss(self) -> float:
        """丢包率 (%)"""
        total = self._frames_sent + self._frames_dropped
        if total == 0:
            return 0.0
        return (self._frames_dropped / total) * 100
    
    def get_quality_score(self) -> int:
        """综合质量评分 (0-100)
        
        评分标准:
        - 延迟 < 50ms: 30 分, < 100ms: 20 分, < 200ms: 10 分, 否则: 0 分
        - 帧率 > 20: 30 分, > 10: 20 分, > 5: 10 分, 否则: 0 分
        - 丢包 < 1%: 20 分, < 5%: 10 分, 否则: 0 分
        - 带宽 > 5Mbps: 20 分, > 2Mbps: 10 分, 否则: 0 分
        """
        score = 0
        
        # 延迟评分 (30 分)
        avg_lat = self.get_avg_latency()
        if avg_lat < 50:
            score += 30
        elif avg_lat < 100:
            score += 20
        elif avg_lat < 200:
            score += 10
        
        # 帧率评分 (30 分)
        fps = self.get_fps()
        if fps > 20:
            score += 30
        elif fps > 10:
            score += 20
        elif fps > 5:
            score += 10
        
        # 丢包评分 (20 分)
        loss = self.get_packet_loss()
        if loss < 1:
            score += 20
        elif loss < 5:
            score += 10
        
        # 带宽评分 (20 分)
        bw = self.get_bandwidth()
        if bw > 5:
            score += 20
        elif bw > 2:
            score += 10
        
        return score
    
    def get_quality_label(self) -> str:
        """质量等级标签"""
        score = self.get_quality_score()
        if score >= 80:
            return "优秀"
        elif score >= 60:
            return "良好"
        elif score >= 40:
            return "一般"
        elif score >= 20:
            return "较差"
        else:
            return "极差"
    
    def get_report(self) -> dict:
        """完整质量报告"""
        return {
            "score": self.get_quality_score(),
            "label": self.get_quality_label(),
            "latency_ms": round(self.get_avg_latency(), 1),
            "latency_p95_ms": round(self.get_p95_latency(), 1),
            "fps": round(self.get_fps(), 1),
            "bandwidth_mbps": round(self.get_bandwidth(), 2),
            "packet_loss_pct": round(self.get_packet_loss(), 2),
            "uptime_seconds": round(time.time() - self._start_time, 1)
        }
    
    def reset(self):
        """重置所有统计"""
        self._latencies = []
        self._frame_times = []
        self._bytes_sent = 0
        self._bytes_received = 0
        self._frames_sent = 0
        self._frames_dropped = 0
        self._last_bandwidth_check = time.time()
        self._start_time = time.time()
        logger.info("📊 质量监控已重置")
