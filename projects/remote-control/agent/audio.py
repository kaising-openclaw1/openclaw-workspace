"""音频转发模块 - 将远程端音频传输到控制端"""
import logging
import io
from typing import Optional

logger = logging.getLogger(__name__)


class AudioStreamer:
    """音频流 - 捕获系统音频并流式传输
    
    注意：Linux 下使用 ALSA/PulseAudio，macOS 使用 CoreAudio，Windows 使用 WASAPI
    """
    
    def __init__(self, sample_rate: int = 48000, channels: int = 2, bitrate: int = 128):
        self.sample_rate = sample_rate
        self.channels = channels
        self.bitrate = bitrate
        self.is_streaming = False
        self._pyaudio = None
        self._stream = None
        logger.info(f"🔊 音频流初始化 ({sample_rate}Hz, {channels}ch, {bitrate}kbps)")
    
    def start(self, callback):
        """开始音频捕获
        
        callback: function(audio_data: bytes) - 接收音频数据
        """
        try:
            import pyaudio
            self._pyaudio = pyaudio.PyAudio()
            
            # 查找默认输入设备
            device_index = self._pyaudio.get_default_input_device_info()["index"]
            
            self._stream = self._pyaudio.open(
                format=pyaudio.paInt16,
                channels=self.channels,
                rate=self.sample_rate,
                input=True,
                input_device_index=device_index,
                frames_per_buffer=1024,
                stream_callback=self._audio_callback
            )
            
            self._callback = callback
            self.is_streaming = True
            self._stream.start_stream()
            
            logger.info("🔊 音频流已启动")
            
        except Exception as e:
            logger.warning(f"⚠️ 音频流启动失败: {e}")
            self._cleanup()
    
    def stop(self):
        """停止音频流"""
        self.is_streaming = False
        self._cleanup()
        logger.info("🔊 音频流已停止")
    
    def _audio_callback(self, in_data, frame_count, time_info, status):
        """音频数据回调"""
        if self._callback and self.is_streaming:
            try:
                self._callback(in_data)
            except Exception as e:
                logger.error(f"音频回调错误: {e}")
        return (in_data, pyaudio.paContinue) if hasattr(self, '_pyaudio') else (None, 0)
    
    def _cleanup(self):
        """清理资源"""
        if self._stream:
            try:
                self._stream.stop_stream()
                self._stream.close()
            except:
                pass
            self._stream = None
        
        if self._pyaudio:
            try:
                self._pyaudio.terminate()
            except:
                pass
            self._pyaudio = None
