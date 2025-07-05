import threading
import time
import queue
import cyal.exceptions
from pyogg import OpusEncoder, OpusDecoder
import cyal
from . import consts
from .speech import speak
from . import options



class voice_chat_compression(threading.Thread):
    def __init__(self, game):
        super().__init__(daemon=True)
        self.game = game
        self.queue = queue.SimpleQueue()
        self.encoder = OpusEncoder()
        self.encoder.set_application('voip')
        self.encoder.set_channels(1)
        self.encoder.set_sampling_frequency(48000)
        self.decoder = OpusDecoder()
        self.decoder.set_channels(1)
        self.decoder.set_sampling_frequency(48000)
        self.start()
    
    def put(self, value):
        self.queue.put_nowait(value)
    
    def run(self):
        while True:
            time.sleep(0.002)
            if self.queue.empty(): continue
            value = self.queue.get_nowait()
            if value is None: break
            if callable(value):
                value()
            if isinstance(value, bytearray):
                buf = self.encoder.encode(value)

                self.game.network.send(
                    consts.CHANNEL_VOICECHAT,
                    "n/a",
                    buf
                )


    def recieve(self, data, vc_source, radio_source, channelID, gameplay):
        self.put(lambda: self.recieve2(data, vc_source, radio_source, channelID, gameplay))

    def recieve2(self, data, vc_source, radio_source, channelID, gameplay):
        buffer = None
        data = bytearray(self.decoder.decode(bytearray(data)))
        with self.game.audio_mngr.context.batch():
            if not gameplay.player.dead:
                if vc_source.buffers_processed > 0: buffer = vc_source.unqueue_buffers()[0]
                else: buffer = self.game.audio_mngr.context.gen_buffer()
                buffer.set_data(data, sample_rate=48000, format=cyal.BufferFormat.MONO16)
                try: vc_source.queue_buffers(buffer)
                except cyal.exceptions.InvalidOperationError: return
                if vc_source.state == cyal.SourceState.STOPPED or vc_source.state == cyal.SourceState.INITIAL: vc_source.play()
            if not gameplay.voice_channels[channelID].has_radio or not gameplay.player.has_radio: return
            if radio_source.buffers_processed > 0: buffer = radio_source.unqueue_buffers()[0]
            else: buffer = self.game.audio_mngr.context.gen_buffer()
            buffer.set_data(data, sample_rate=48000, format=cyal.BufferFormat.MONO16)
            radio_source.queue_buffers(buffer)
            if radio_source.state == cyal.SourceState.STOPPED or radio_source.state == cyal.SourceState.INITIAL: radio_source.play()


class VoiceChatRecord(threading.Thread):
    def __init__(self, game, player):
        super().__init__(daemon=True)
        self.game = game
        self.player = player
        self.capture_ext = cyal.CaptureExtension()
        device = options.get("audio_input_device", 'system default')
        if device == 'system default': device = self.capture_ext.default_device.decode('utf-8')
        try: self.audio_input = self.capture_ext.open_device(name=device.encode(), sample_rate=48000)
        except cyal.exceptions.DeviceNotFoundError: 
            self.audio_input = None
            speak(f"Failed to load audio device: {device}")
        self.vc_compression = voice_chat_compression(self.game)
        self.recording = False
        self.running = True
        self.start()
    

    def run(self):
        while self.running:
            time.sleep(0.0005)
            if not self.recording: continue
            if self.audio_input is None or not options.get("microphone", True) or not options.get("voice_chat", True): continue
            samples = self.audio_input.available_samples
            if samples >= 960:
                buf = bytearray(960 * 2)
                self.audio_input.capture_samples(buf)
                self.vc_compression.put(buf)

    def voice_chat_finish(self):
        self.voice_chat_finish2()
    
    def voice_chat_finish2(self):
        if self.audio_input.available_samples < 960: return self.audio_input.capture_samples(bytearray(self.audio_input.available_samples*2))
        buf = bytearray(1920)
        self.audio_input.capture_samples(buf)
        self.vc_compression.put(buf)
    
    def close(self):
        self.vc_compression.put(None)
        self.running = False
        
