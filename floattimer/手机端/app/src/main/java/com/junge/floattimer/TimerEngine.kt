package com.junge.floattimer

import android.os.Handler
import android.os.Looper
import android.os.SystemClock

/**
 * 计时核心：50ms 循环刷新，支持正计时 / 倒计时 / 番茄钟。
 * 单例，供 MainActivity 与 FloatService 共享同一份计时状态。
 */
object TimerEngine {

    const val MODE_COUNT_UP = 0
    const val MODE_COUNT_DOWN = 1
    const val MODE_POMODORO = 2

    var mode = MODE_COUNT_UP
        private set

    /** 倒计时总时长（毫秒） */
    var countdownTotalMs = 5 * 60 * 1000L
        private set

    /** 番茄钟：专注时长 / 休息时长（毫秒） */
    var pomodoroWorkMs = 25 * 60 * 1000L
        private set
    var pomodoroBreakMs = 5 * 60 * 1000L
        private set

    /** 番茄钟当前是否处于「休息」阶段 */
    var isBreak = false
        private set

    /** 番茄钟已完成专注轮数 */
    var pomodoroRound = 0
        private set

    /** 番茄钟阶段切换回调：true=进入休息，false=进入下一轮专注 */
    var onPhaseSwitch: ((Boolean) -> Unit)? = null

    /** 番茄钟当前阶段总时长 */
    val pomodoroPhaseTotalMs: Long
        get() = if (isBreak) pomodoroBreakMs else pomodoroWorkMs

    var running = false
        private set

    /** 正计时到时提醒分钟数，0=关闭提醒 */
    @Volatile
    var alertMinutes = 0
        private set

    /** 本次正计时是否已触发过到时提醒（只提醒一次，重置/改设置后清除） */
    @Volatile
    private var alerted = false

    /** 倒计时「结束前提醒」开关，默认开启 */
    @Volatile
    var preAlertEnabled = true
        private set

    /** 倒计时结束前多少秒触发提醒，默认 3 秒 */
    @Volatile
    var preAlertSeconds = 3
        private set

    /** 本轮倒计时是否已触发过结束前提醒（重置/重新开始后清除） */
    @Volatile
    private var preAlerted = false

    /** 正计时：已累计毫秒；倒计时：剩余毫秒 */
    var displayMs = 0L
        private set

    private var lastTickRealtime = 0L
    private val handler = Handler(Looper.getMainLooper())

    private var onTick: ((Long) -> Unit)? = null
    private var onFinish: (() -> Unit)? = null

    /** 正计时到达设定分钟数时的回调（只触发一次，计时继续走） */
    var onAlert: (() -> Unit)? = null

    /** 倒计时剩余设定秒数时的回调（入参=设定秒数，只触发一次，计时继续走） */
    var onPreAlert: ((Int) -> Unit)? = null

    private val loop = object : Runnable {
        override fun run() {
            if (!running) return
            val now = SystemClock.elapsedRealtime()
            val delta = now - lastTickRealtime
            lastTickRealtime = now
            if (mode == MODE_COUNT_UP) {
                displayMs += delta
                // 正计时到时提醒：达到设定分钟数且尚未提醒过，则触发一次（计时不中断）
                if (alertMinutes > 0 && !alerted && displayMs >= alertMinutes * 60_000L) {
                    alerted = true
                    onAlert?.invoke()
                }
            } else {
                displayMs -= delta
                // 结束前提醒：剩余时间首次进入设定秒数以内（且尚未结束）时触发一次，计时不中断
                if (preAlertEnabled && preAlertSeconds > 0 && !preAlerted &&
                    displayMs > 0L && displayMs <= preAlertSeconds * 1000L
                ) {
                    preAlerted = true
                    onPreAlert?.invoke(preAlertSeconds)
                }
                if (displayMs <= 0L) {
                    if (mode == MODE_POMODORO) {
                        // 番茄钟：阶段到点不停表，自动切到下一阶段继续走
                        switchPomodoroPhase()
                    } else {
                        displayMs = 0L
                        running = false
                        onTick?.invoke(displayMs)
                        onFinish?.invoke()
                        return
                    }
                }
            }
            onTick?.invoke(displayMs)
            handler.postDelayed(this, 50)
        }
    }

    fun setListeners(tick: (Long) -> Unit, finish: () -> Unit) {
        onTick = tick
        onFinish = finish
    }

    fun removeListeners() {
        onTick = null
        onFinish = null
    }

    fun setMode(newMode: Int) {
        if (running) return
        mode = newMode
        alerted = false
        preAlerted = false
        isBreak = false
        pomodoroRound = 0
        displayMs = when (mode) {
            MODE_COUNT_UP -> 0L
            MODE_COUNT_DOWN -> countdownTotalMs
            else -> pomodoroWorkMs
        }
        onTick?.invoke(displayMs)
    }

    /** 番茄钟阶段切换：专注结束→休息；休息结束→下一轮专注（计时不中断） */
    private fun switchPomodoroPhase() {
        preAlerted = false
        if (isBreak) {
            isBreak = false
            displayMs = pomodoroWorkMs
            onPhaseSwitch?.invoke(false)
        } else {
            pomodoroRound++
            isBreak = true
            displayMs = pomodoroBreakMs
            onPhaseSwitch?.invoke(true)
        }
    }

    /** 设置番茄钟专注/休息分钟数（未运行时生效，回到第一轮专注） */
    fun setPomodoroMinutes(workMin: Int, breakMin: Int) {
        if (running) return
        pomodoroWorkMs = workMin.coerceIn(1, 600) * 60L * 1000L
        pomodoroBreakMs = breakMin.coerceIn(1, 600) * 60L * 1000L
        isBreak = false
        pomodoroRound = 0
        preAlerted = false
        if (mode == MODE_POMODORO) {
            displayMs = pomodoroWorkMs
            onTick?.invoke(displayMs)
        }
    }

    /** 设置正计时到时提醒分钟数（0=关闭），值变化时清除已提醒标记 */
    fun setAlertMinutes(minutes: Int) {
        val v = minutes.coerceAtLeast(0)
        if (alertMinutes != v) alerted = false
        alertMinutes = v
    }

    fun setCountdownMinutes(minutes: Int) {
        setCountdownSeconds(minutes.toLong() * 60)
    }

    /** 按秒设定倒计时总时长（支持任意秒数，如 90 秒） */
    fun setCountdownSeconds(seconds: Long) {
        if (running) return
        countdownTotalMs = seconds.coerceAtLeast(0) * 1000L
        if (mode == MODE_COUNT_DOWN) {
            displayMs = countdownTotalMs
            preAlerted = false
            onTick?.invoke(displayMs)
        }
    }

    /** 设置倒计时结束前提醒：enabled=false 关闭；seconds 为提前秒数（默认3） */
    fun setPreAlert(enabled: Boolean, seconds: Int) {
        preAlertEnabled = enabled
        preAlertSeconds = seconds.coerceIn(1, 3600)
        preAlerted = false
    }

    fun start() {
        if (running) return
        if (mode == MODE_COUNT_DOWN && displayMs <= 0L) {
            displayMs = countdownTotalMs
            preAlerted = false
        }
        if (mode == MODE_POMODORO && displayMs <= 0L) {
            displayMs = pomodoroPhaseTotalMs
            preAlerted = false
        }
        running = true
        lastTickRealtime = SystemClock.elapsedRealtime()
        handler.post(loop)
    }

    fun pause() {
        running = false
        handler.removeCallbacks(loop)
    }

    fun reset() {
        running = false
        handler.removeCallbacks(loop)
        alerted = false
        preAlerted = false
        isBreak = false
        pomodoroRound = 0
        displayMs = when (mode) {
            MODE_COUNT_UP -> 0L
            MODE_COUNT_DOWN -> countdownTotalMs
            else -> pomodoroWorkMs
        }
        onTick?.invoke(displayMs)
    }

    /**
     * 是否处于"暂停中"：已开始过、尚未结束、当前未运行。
     * 正计时：已累加过时间；倒计时：剩余时间在 (0, 总时长) 之间。
     * 用于区分"从未开始/已自然结束"（双击应开始）与"暂停中"（双击应停止）。
     */
    fun isPausedMid(): Boolean {
        if (running) return false
        return when (mode) {
            MODE_COUNT_UP -> displayMs > 0L
            MODE_COUNT_DOWN -> displayMs > 0L && displayMs < countdownTotalMs
            else -> displayMs > 0L && displayMs < pomodoroPhaseTotalMs
        }
    }

    /**
     * 停止本次计时：计算本次已进行秒数，随后归零回到初始状态。
     * @return 本次已进行的时长（秒）。正计时=已累加；倒计时/番茄钟=本阶段总时长-剩余。
     */
    fun stop(): Long {
        val elapsedMs = when (mode) {
            MODE_COUNT_UP -> displayMs
            MODE_COUNT_DOWN -> countdownTotalMs - displayMs
            else -> pomodoroPhaseTotalMs - displayMs
        }
        running = false
        handler.removeCallbacks(loop)
        preAlerted = false
        isBreak = false
        pomodoroRound = 0
        displayMs = when (mode) {
            MODE_COUNT_UP -> 0L
            MODE_COUNT_DOWN -> countdownTotalMs
            else -> pomodoroWorkMs
        }
        onTick?.invoke(displayMs)
        return elapsedMs / 1000
    }

    /** 格式化显示：正计时超过1小时显示 HH:mm:ss，否则 mm:ss */
    fun format(ms: Long): String {
        val totalSec = ms / 1000
        val h = totalSec / 3600
        val m = (totalSec % 3600) / 60
        val s = totalSec % 60
        return if (h > 0) String.format("%02d:%02d:%02d", h, m, s)
        else String.format("%02d:%02d", m, s)
    }

    /** 悬浮球短格式 mm:ss（超1小时显示 H:MM:SS 简化） */
    fun formatShort(ms: Long): String {
        val totalSec = ms / 1000
        val h = totalSec / 3600
        val m = (totalSec % 3600) / 60
        val s = totalSec % 60
        return if (h > 0) String.format("%d:%02d:%02d", h, m, s)
        else String.format("%02d:%02d", m, s)
    }
}
