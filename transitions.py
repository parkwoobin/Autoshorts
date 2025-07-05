import numpy as np
import cv2
from moviepy.editor import VideoClip, AudioFileClip, CompositeAudioClip
from video_models import VideoConfig

# 트랜지션 설정값
duration = VideoConfig.TRANSITION_DURATION
target_w, target_h = VideoConfig.RESOLUTION_WIDTH, VideoConfig.RESOLUTION_HEIGHT
split = 0.4  # A 40%, B 60% 시간 분할

# 효과음 경로
audio_paths = {
    "zoom": "./effect/zoom.mp3",
    "pan": "./effect/pan.mp3",
    "rotate": "./effect/rotate.mp3",
}

def attach_audio_to_transition(clip, audio_path):
    audio = AudioFileClip(audio_path).subclip(0, min(clip.duration, AudioFileClip(audio_path).duration))
    return clip.set_audio(audio)

class SmoothTransitions:

    @staticmethod
    def ease_in(t): return t * t

    @staticmethod
    def ease_out(t): return 1 - (1 - t) * (1 - t)

    @staticmethod
    def resize_and_center(frame, scale, target_size):
        h, w = frame.shape[:2]
        new_w, new_h = max(1, int(w * scale)), max(1, int(h * scale))
        resized = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_CUBIC)
        cx, cy = new_w // 2, new_h // 2
        x1 = max(0, cx - target_size[0] // 2)
        y1 = max(0, cy - target_size[1] // 2)
        x2, y2 = x1 + target_size[0], y1 + target_size[1]
        return resized[y1:y2, x1:x2]

    @staticmethod
    def zoom_in(a, b, duration=duration):
        a_start, b_start = max(0, a.duration - duration), 0.0
        def make_frame(t):
            p = t / duration
            fa = a.get_frame(a_start + t)
            fb = b.get_frame(b_start + t)
            if p <= split:
                pa = SmoothTransitions.ease_in(p / split)
                scale_a = 1.0 + 1.0 * pa
                return SmoothTransitions.resize_and_center(fa, scale_a, (target_w, target_h))
            else:
                pb = SmoothTransitions.ease_out((p - split) / (1.0 - split))
                scale_b = pb
                return SmoothTransitions.resize_and_center(fb, scale_b, (target_w, target_h))
        clip = VideoClip(make_frame, duration=duration)
        return attach_audio_to_transition(clip, audio_paths["zoom"])

    @staticmethod
    def zoom_out(a, b, duration=duration):
        a_start, b_start = max(0, a.duration - duration), 0.0
        def make_frame(t):
            p = t / duration
            fa = a.get_frame(a_start + t)
            fb = b.get_frame(b_start + t)
            if p <= split:
                pa = SmoothTransitions.ease_in(p / split)
                scale_a = 1.0 - 0.5 * pa
                return SmoothTransitions.resize_and_center(fa, scale_a, (target_w, target_h))
            else:
                pb = SmoothTransitions.ease_out((p - split) / (1.0 - split))
                scale_b = 3.0 - 2.0 * pb
                return SmoothTransitions.resize_and_center(fb, scale_b, (target_w, target_h))
        clip = VideoClip(make_frame, duration=duration)
        return attach_audio_to_transition(clip, audio_paths["zoom"])

    @staticmethod
    def pan(a, b, direction='right', duration=duration):
        a_start = max(0, a.duration - duration)
        def make_frame(t):
            p = t / duration
            fa = a.get_frame(a_start + t)
            fb = b.get_frame(t)
            fa = cv2.resize(fa, (target_w, target_h))
            fb = cv2.resize(fb, (target_w, target_h))

            if direction in ['left', 'right']:
                max_offset = target_w
            else:
                max_offset = target_h

            # 중앙 겹침을 보장하는 동기화 offset
            smooth_p = (1 - np.cos(p * np.pi)) / 2
            offset = int(max_offset * smooth_p)
            offset_a = offset
            offset_b = max_offset - offset

            # 방향별 이동 matrix
            if direction == 'left':
                Ma = np.float32([[1, 0, -offset_a], [0, 1, 0]])
                Mb = np.float32([[1, 0, offset_b], [0, 1, 0]])
            elif direction == 'right':
                Ma = np.float32([[1, 0, offset_a], [0, 1, 0]])
                Mb = np.float32([[1, 0, -offset_b], [0, 1, 0]])
            elif direction == 'up':
                Ma = np.float32([[1, 0, 0], [0, 1, -offset_a]])
                Mb = np.float32([[1, 0, 0], [0, 1, offset_b]])
            else:  # down
                Ma = np.float32([[1, 0, 0], [0, 1, offset_a]])
                Mb = np.float32([[1, 0, 0], [0, 1, -offset_b]])

            wa = cv2.warpAffine(fa, Ma, (target_w, target_h))
            wb = cv2.warpAffine(fb, Mb, (target_w, target_h))

            return cv2.addWeighted(wa, 1 - smooth_p, wb, smooth_p, 0)
        clip = VideoClip(make_frame, duration=duration)
        return attach_audio_to_transition(clip, audio_paths["pan"])

    @staticmethod
    def rotate(a, b, clockwise=True, duration=duration):
        a_start, b_start = max(0, a.duration - duration), 0.0
        center = (target_w // 2, target_h // 2)
        def make_frame(t):
            p = t / duration
            fa = a.get_frame(a_start + t)
            fb = b.get_frame(b_start + t)
            fa = cv2.resize(fa, (target_w, target_h))
            fb = cv2.resize(fb, (target_w, target_h))
            if p <= split:
                angle = 100 * SmoothTransitions.ease_in(p / split)
                M = cv2.getRotationMatrix2D(center, angle if clockwise else -angle, 1.0)
                return cv2.warpAffine(fa, M, (target_w, target_h))
            else:
                pb = SmoothTransitions.ease_out((p - split) / (1.0 - split))
                angle = 100 + 260 * pb
                M = cv2.getRotationMatrix2D(center, angle if clockwise else -angle, 1.0)
                return cv2.warpAffine(fb, M, (target_w, target_h))
        clip = VideoClip(make_frame, duration=duration)
        return attach_audio_to_transition(clip, audio_paths["rotate"])

    @staticmethod
    def fade(a, b, duration=duration):
        a_start, b_start = max(0, a.duration - duration), 0.0
        def make_frame(t):
            p = (1 - np.cos(t / duration * np.pi)) / 2
            fa = a.get_frame(a_start + t)
            fb = b.get_frame(b_start + t)
            fa = cv2.resize(fa, (target_w, target_h))
            fb = cv2.resize(fb, (target_w, target_h))
            return cv2.addWeighted(fa, 1 - p, fb, p, 0)
        return VideoClip(make_frame, duration=duration)


class VideoTransitions:

    @staticmethod
    def get_available_transitions():
        return [
            ("zoom_in", "줌 인"),
            ("zoom_out", "줌 아웃"),
            ("pan_right", "우로 패닝"),
            ("pan_left", "좌로 패닝"),
            ("pan_up", "위로 패닝"),
            ("pan_down", "아래로 패닝"),
            ("rotate_clockwise", "시계방향 회전"),
            ("rotate_counter_clockwise", "반시계방향 회전"),
            ("fade", "페이드")
        ]

    @staticmethod
    def create_transition(clip_a, clip_b, transition_type, duration=VideoConfig.TRANSITION_DURATION):
        if transition_type == "zoom_in":
            return SmoothTransitions.zoom_in(clip_a, clip_b, duration)
        elif transition_type == "zoom_out":
            return SmoothTransitions.zoom_out(clip_a, clip_b, duration)
        elif transition_type == "pan_right":
            return SmoothTransitions.pan(clip_a, clip_b, 'right', duration)
        elif transition_type == "pan_left":
            return SmoothTransitions.pan(clip_a, clip_b, 'left', duration)
        elif transition_type == "pan_up":
            return SmoothTransitions.pan(clip_a, clip_b, 'up', duration)
        elif transition_type == "pan_down":
            return SmoothTransitions.pan(clip_a, clip_b, 'down', duration)
        elif transition_type == "rotate_clockwise":
            return SmoothTransitions.rotate(clip_a, clip_b, True, duration)
        elif transition_type == "rotate_counter_clockwise":
            return SmoothTransitions.rotate(clip_a, clip_b, False, duration)
        elif transition_type == "fade":
            return SmoothTransitions.fade(clip_a, clip_b, duration)
        else:
            raise ValueError(f"지원되지 않는 트랜지션 타입: {transition_type}")
