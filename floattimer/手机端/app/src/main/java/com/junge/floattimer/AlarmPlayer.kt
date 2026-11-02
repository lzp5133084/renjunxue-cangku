package com.junge.floattimer

import android.content.Context
import android.media.AudioAttributes
import android.media.AudioManager
import android.media.Ringtone
import android.media.RingtoneManager
import android.os.Build
import android.os.Handler
import android.os.Looper
import android.os.VibrationEffect
import android.os.Vibrator
import android.os.VibratorManager

/**
 * 计时结束提醒播放器。
 * 说明：旧版只依赖通知渠道的默认提示音，很多机型通知音被系统压得很轻、几乎听不到。
 * 这里改为显式播放「闹钟铃声」（AudioAttributes USAGE_ALARM，走闹钟音量通道），
 * 并配合震动，保证一定能被察觉；默认响 8 秒后自动停止。
 */
object AlarmPlayer {

    private var ringtone: Ringtone? = null
    private val handler = Handler(Looper.getMainLooper())

    /** 播放到时提醒：响铃 [seconds] 秒 + 震动（可重复调用，会先停掉上一次） */
    fun play(context: Context, seconds: Int = 8) {
        stop()
        val app = context.applicationContext
        try {
            val uri = RingtoneManager.getDefaultUri(RingtoneManager.TYPE_ALARM)
                ?: RingtoneManager.getDefaultUri(RingtoneManager.TYPE_NOTIFICATION)
            val r = RingtoneManager.getRingtone(app, uri)
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.LOLLIPOP) {
                r.audioAttributes = AudioAttributes.Builder()
                    .setUsage(AudioAttributes.USAGE_ALARM)
                    .setContentType(AudioAttributes.CONTENT_TYPE_SONIFICATION)
                    .build()
            }
            r.play()
            ringtone = r
            handler.postDelayed({ stop() }, seconds * 1000L)
        } catch (_: Exception) {
        }
        vibrate(app)
    }

    /** 停止响铃（幂等） */
    fun stop() {
        try {
            ringtone?.stop()
        } catch (_: Exception) {
        }
        ringtone = null
    }

    @Suppress("DEPRECATION")
    private fun vibrate(context: Context) {
        try {
            val v: Vibrator? = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
                (context.getSystemService(Context.VIBRATOR_MANAGER_SERVICE) as VibratorManager)
                    .defaultVibrator
            } else {
                context.getSystemService(Context.VIBRATOR_SERVICE) as Vibrator
            }
            if (v == null || !v.hasVibrator()) return
            val pattern = longArrayOf(0, 600, 300, 600, 300, 900)
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                v.vibrate(VibrationEffect.createWaveform(pattern, -1))
            } else {
                v.vibrate(pattern, -1)
            }
        } catch (_: Exception) {
        }
    }
}
