package com.junge.floattimer

import android.Manifest
import android.app.DownloadManager
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.content.pm.PackageManager
import android.media.AudioManager
import android.media.ToneGenerator
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.os.Environment
import android.os.Handler
import android.os.Looper
import android.provider.Settings
import android.speech.tts.TextToSpeech
import android.text.Editable
import android.text.TextWatcher
import android.view.View
import android.widget.Button
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity
import androidx.appcompat.widget.SwitchCompat
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat
import androidx.core.content.FileProvider
import androidx.recyclerview.widget.LinearLayoutManager
import androidx.recyclerview.widget.RecyclerView
import org.json.JSONObject
import java.io.File
import java.net.HttpURLConnection
import java.net.URL
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

/**
 * 主界面：正计时/倒计时切换、预设时长、开始/暂停/重置、
 * 当前系统时间、命名保存开关、悬浮球开关、使用记录列表。
 * 作者：军哥懂保（微信号：xunijiayuan）
 */
class MainActivity : AppCompatActivity() {

    companion object {
        const val PREFS = "float_timer_prefs"
        const val KEY_ASK_NAME = "ask_name_on_finish"
        const val KEY_ALERT_MINUTES = "alert_minutes"
        const val KEY_ALERT_ENABLED = "alert_enabled"
        /** 倒计时结束前语音提醒：开关 + 提前秒数 */
        const val KEY_PRE_ALERT_ENABLED = "pre_alert_enabled"
        const val KEY_PRE_ALERT_SEC = "pre_alert_seconds"
        /** 番茄钟：专注分钟 / 休息分钟 */
        const val KEY_POMO_WORK = "pomo_work_minutes"
        const val KEY_POMO_BREAK = "pomo_break_minutes"
        /** 上次计时（用于「重复上次」）：模式 + 时长秒数 */
        const val KEY_LAST_MODE = "last_timer_mode"
        const val KEY_LAST_SECONDS = "last_timer_seconds"
        const val EXTRA_SHOW_NAME_DIALOG = "show_name_dialog"
        /** 悬浮球双击停止后，拉起本界面并弹出命名保存对话框 */
        const val EXTRA_SHOW_STOP_DIALOG = "show_stop_dialog"
        const val EXTRA_SHOW_SHARE_DIALOG = "show_share_dialog"
        /** 悬浮球菜单"退出程序"广播，收到后主界面关闭 */
        const val ACTION_EXIT_APP = "com.junge.floattimer.EXIT_APP"
        /** 版本检查服务端地址 */
        const val VERSION_CHECK_URL = "https://ecojia.cn/timer/version.json"
        /** 广告配置服务端地址（三端统一，后期替换广告商只需改此配置与视频） */
        const val AD_CONFIG_URL = "https://ecojia.cn/timer/ad.json"

        @Volatile
        var isForeground = false

        /** 悬浮球双击停止时暂存的本次计时秒数，由主界面取出并走命名保存流程 */
        @Volatile
        var pendingStopSeconds = -1L
    }

    private lateinit var db: TimerDbHelper
    private lateinit var adapter: RecordAdapter
    private val handler = Handler(Looper.getMainLooper())
    private val clockFormat = SimpleDateFormat("HH:mm:ss", Locale.CHINA)

    private lateinit var tvBigTime: TextView
    private lateinit var tvClock: TextView
    private lateinit var tvRecordEmpty: TextView
    private lateinit var btnModeUp: Button
    private lateinit var btnModeDown: Button
    private lateinit var layoutPresets: LinearLayout
    private lateinit var btnStartPause: Button
    private lateinit var btnStop: Button
    private lateinit var layoutPermission: LinearLayout
    private lateinit var switchAskName: SwitchCompat
    private lateinit var editAlertMinutes: EditText
    private lateinit var switchAlert: SwitchCompat
    private lateinit var btnCustomTime: Button
    private lateinit var editPreAlertSec: EditText
    private lateinit var switchPreAlert: SwitchCompat
    private lateinit var btnModePomodoro: Button
    private lateinit var btnPomodoroSetting: Button
    private lateinit var tvPhaseLabel: TextView
    private lateinit var btnLap: Button
    private lateinit var btnRepeat: Button
    private lateinit var layoutLaps: LinearLayout
    private lateinit var tvLapList: TextView

    /** 计次记录：每项为 (本段毫秒, 累计毫秒) */
    private val laps = mutableListOf<Pair<Long, Long>>()

    /** 语音播报（TTS）：结束前提醒与到时播报共用 */
    private var tts: TextToSpeech? = null
    private var ttsReady = false

    /** 倒计时自然结束时的时长（秒），用于命名对话框保存 */
    private var pendingFinishSeconds = -1L

    /** 接收悬浮球菜单"退出程序"广播，关闭主界面 */
    private val exitReceiver = object : BroadcastReceiver() {
        override fun onReceive(context: Context?, intent: Intent?) {
            finish()
        }
    }

    private val clockLoop = object : Runnable {
        override fun run() {
            tvClock.text = "当前时间 " + clockFormat.format(Date())
            handler.postDelayed(this, 1000)
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        db = TimerDbHelper(this)
        bindViews()
        loadPomodoroPrefs()
        setupModeButtons()
        setupPresets()
        setupControlButtons()
        setupSwitch()
        setupAlertSetting()
        setupPreAlertSetting()
        setupRecords()
        setupPermissionBanner()
        initTts()

        TimerEngine.setListeners(
            tick = { ms -> runOnUiThread { tvBigTime.text = TimerEngine.format(ms) } },
            finish = {
                runOnUiThread {
                    onTimerFinished()
                }
            }
        )
        // 正计时到时提醒：响铃 + Toast 提示，计时继续走
        TimerEngine.onAlert = {
            runOnUiThread { onCountUpAlert() }
        }
        // 倒计时结束前提醒：语音播报 + 提示音，计时继续走
        TimerEngine.onPreAlert = { sec ->
            runOnUiThread { onPreAlert(sec) }
        }
        // 番茄钟阶段切换：专注↔休息自动衔接，语音播报 + 提示音
        TimerEngine.onPhaseSwitch = { toBreak ->
            runOnUiThread { onPomodoroPhaseSwitch(toBreak) }
        }
        tvBigTime.text = TimerEngine.format(TimerEngine.displayMs)
        refreshControlButtons()
        handleNameDialogIntent(intent)
        handleStopIntent(intent)

        // 注册"退出程序"广播接收器（仅本应用内部）
        ContextCompat.registerReceiver(
            this, exitReceiver, IntentFilter(ACTION_EXIT_APP),
            ContextCompat.RECEIVER_NOT_EXPORTED
        )

        if (Build.VERSION.SDK_INT >= 33 &&
            ContextCompat.checkSelfPermission(this, Manifest.permission.POST_NOTIFICATIONS)
            != PackageManager.PERMISSION_GRANTED
        ) {
            ActivityCompat.requestPermissions(
                this, arrayOf(Manifest.permission.POST_NOTIFICATIONS), 100
            )
        }

        // 启动2秒后后台检查更新
        Handler(Looper.getMainLooper()).postDelayed({ checkUpdate() }, 2000)
        // 启动1.5秒后尝试加载广告（后台拉取配置，失败静默跳过）
        Handler(Looper.getMainLooper()).postDelayed({ loadAd() }, 1500)
    }

    private fun bindViews() {
        tvBigTime = findViewById(R.id.tvBigTime)
        tvClock = findViewById(R.id.tvClock)
        tvRecordEmpty = findViewById(R.id.tvRecordEmpty)
        btnModeUp = findViewById(R.id.btnModeUp)
        btnModeDown = findViewById(R.id.btnModeDown)
        layoutPresets = findViewById(R.id.layoutPresets)
        btnStartPause = findViewById(R.id.btnStartPause)
        btnStop = findViewById(R.id.btnStop)
        layoutPermission = findViewById(R.id.layoutPermission)
        switchAskName = findViewById(R.id.switchAskName)
        editAlertMinutes = findViewById(R.id.editAlertMinutes)
        switchAlert = findViewById(R.id.switchAlert)
        btnCustomTime = findViewById(R.id.btnCustomTime)
        editPreAlertSec = findViewById(R.id.editPreAlertSec)
        switchPreAlert = findViewById(R.id.switchPreAlert)
        btnModePomodoro = findViewById(R.id.btnModePomodoro)
        btnPomodoroSetting = findViewById(R.id.btnPomodoroSetting)
        tvPhaseLabel = findViewById(R.id.tvPhaseLabel)
        btnLap = findViewById(R.id.btnLap)
        btnRepeat = findViewById(R.id.btnRepeat)
        layoutLaps = findViewById(R.id.layoutLaps)
        tvLapList = findViewById(R.id.tvLapList)
    }

    private fun setupModeButtons() {
        btnModeUp.setOnClickListener {
            TimerEngine.setMode(TimerEngine.MODE_COUNT_UP)
            laps.clear()
            refreshModeUI()
        }
        btnModeDown.setOnClickListener {
            TimerEngine.setMode(TimerEngine.MODE_COUNT_DOWN)
            laps.clear()
            refreshModeUI()
        }
        btnModePomodoro.setOnClickListener {
            TimerEngine.setMode(TimerEngine.MODE_POMODORO)
            laps.clear()
            refreshModeUI()
            Toast.makeText(
                this,
                "🍅 番茄钟：专注 ${TimerEngine.pomodoroWorkMs / 60000} 分钟 + 休息 ${TimerEngine.pomodoroBreakMs / 60000} 分钟",
                Toast.LENGTH_SHORT
            ).show()
        }
        refreshModeUI()
    }

    private fun refreshModeUI() {
        val mode = TimerEngine.mode
        btnModeUp.setBackgroundResource(
            if (mode == TimerEngine.MODE_COUNT_UP) R.drawable.bg_mode_selected else R.drawable.bg_mode_unselected
        )
        btnModeDown.setBackgroundResource(
            if (mode == TimerEngine.MODE_COUNT_DOWN) R.drawable.bg_mode_selected else R.drawable.bg_mode_unselected
        )
        btnModePomodoro.setBackgroundResource(
            if (mode == TimerEngine.MODE_POMODORO) R.drawable.bg_mode_selected else R.drawable.bg_mode_unselected
        )
        val isDown = mode == TimerEngine.MODE_COUNT_DOWN
        val isPomodoro = mode == TimerEngine.MODE_POMODORO
        layoutPresets.visibility = if (isDown) View.VISIBLE else View.GONE
        btnCustomTime.visibility = if (isDown) View.VISIBLE else View.GONE
        btnPomodoroSetting.visibility = if (isPomodoro) View.VISIBLE else View.GONE
        tvPhaseLabel.visibility = if (isPomodoro) View.VISIBLE else View.GONE
        btnPomodoroSetting.text =
            "⚙ 番茄设置（专注 ${TimerEngine.pomodoroWorkMs / 60000} / 休息 ${TimerEngine.pomodoroBreakMs / 60000} 分钟）"
        refreshPhaseLabel()
        tvBigTime.text = TimerEngine.format(TimerEngine.displayMs)
        refreshLaps()
    }

    /** 番茄钟阶段标签：显示当前是专注还是休息、第几轮 */
    private fun refreshPhaseLabel() {
        if (TimerEngine.mode != TimerEngine.MODE_POMODORO) return
        tvPhaseLabel.text = if (TimerEngine.isBreak) {
            "☕ 休息中 · 已完成 ${TimerEngine.pomodoroRound} 轮专注"
        } else {
            "🍅 专注中 · 第 ${TimerEngine.pomodoroRound + 1} 轮"
        }
    }

    /** 番茄钟参数设置对话框：专注 / 休息分钟数 */
    private fun showPomodoroDialog() {
        val view = layoutInflater.inflate(R.layout.dialog_pomodoro, null)
        val ew = view.findViewById<EditText>(R.id.editPomoWork)
        val eb = view.findViewById<EditText>(R.id.editPomoBreak)
        ew.setText((TimerEngine.pomodoroWorkMs / 60000).toString())
        eb.setText((TimerEngine.pomodoroBreakMs / 60000).toString())

        AlertDialog.Builder(this)
            .setTitle("🍅 番茄钟参数设置")
            .setView(view)
            .setPositiveButton("确定") { _, _ ->
                val work = ew.text.toString().trim().toIntOrNull() ?: 25
                val rest = eb.text.toString().trim().toIntOrNull() ?: 5
                if (work <= 0 || rest <= 0) {
                    Toast.makeText(this, "时长必须大于 0 分钟", Toast.LENGTH_SHORT).show()
                    return@setPositiveButton
                }
                getSharedPreferences(PREFS, MODE_PRIVATE).edit()
                    .putInt(KEY_POMO_WORK, work)
                    .putInt(KEY_POMO_BREAK, rest)
                    .apply()
                TimerEngine.setPomodoroMinutes(work, rest)
                refreshModeUI()
                Toast.makeText(this, "已设置：专注 $work 分钟 / 休息 $rest 分钟", Toast.LENGTH_SHORT).show()
            }
            .setNegativeButton("取消", null)
            .show()
    }

    private fun setupPresets() {
        val presets = mapOf(
            R.id.btnPreset1 to 1, R.id.btnPreset5 to 5,
            R.id.btnPreset10 to 10, R.id.btnPreset25 to 25
        )
        for ((id, min) in presets) {
            findViewById<Button>(id).setOnClickListener {
                TimerEngine.setMode(TimerEngine.MODE_COUNT_DOWN)
                TimerEngine.setCountdownMinutes(min)
                refreshModeUI()
                Toast.makeText(this, "已设置倒计时 $min 分钟", Toast.LENGTH_SHORT).show()
            }
        }
        // 自定义时长：精确到任意秒
        btnCustomTime.setOnClickListener { showCustomTimeDialog() }
    }

    /** 自定义倒计时时长对话框：时/分/秒三段输入，合计换算成总秒数 */
    private fun showCustomTimeDialog() {
        val view = layoutInflater.inflate(R.layout.dialog_custom_time, null)
        val eh = view.findViewById<EditText>(R.id.editHour)
        val em = view.findViewById<EditText>(R.id.editMinute)
        val es = view.findViewById<EditText>(R.id.editSecond)
        // 预填当前倒计时设置，便于在原值上微调
        val total = TimerEngine.countdownTotalMs / 1000
        eh.setText((total / 3600).toString())
        em.setText(((total % 3600) / 60).toString())
        es.setText((total % 60).toString())

        AlertDialog.Builder(this)
            .setTitle("⏳ 自定义倒计时时长")
            .setView(view)
            .setPositiveButton("确定") { _, _ ->
                val h = eh.text.toString().trim().toLongOrNull() ?: 0L
                val m = em.text.toString().trim().toLongOrNull() ?: 0L
                val s = es.text.toString().trim().toLongOrNull() ?: 0L
                val seconds = h * 3600 + m * 60 + s
                if (seconds <= 0) {
                    Toast.makeText(this, "时长必须大于 0 秒", Toast.LENGTH_SHORT).show()
                    return@setPositiveButton
                }
                TimerEngine.setMode(TimerEngine.MODE_COUNT_DOWN)
                TimerEngine.setCountdownSeconds(seconds)
                refreshModeUI()
                Toast.makeText(this, "已设置倒计时 ${TimerEngine.format(seconds * 1000)}",
                    Toast.LENGTH_SHORT).show()
            }
            .setNegativeButton("取消", null)
            .show()
    }

    private fun setupControlButtons() {
        btnStartPause.setOnClickListener {
            if (TimerEngine.running) {
                TimerEngine.pause()
            } else {
                rememberLastTimer()
                TimerEngine.start()
            }
            refreshControlButtons()
        }
        btnStop.setOnClickListener {
            // 停止：结束本次计时并按需弹命名框，然后归零
            val seconds = TimerEngine.stop()
            laps.clear()
            refreshLaps()
            refreshPhaseLabel()
            refreshControlButtons()
            offerSaveAfterStop(seconds)
        }
        findViewById<Button>(R.id.btnReset).setOnClickListener {
            // 重置：仅清零回到初始状态，不弹命名框
            TimerEngine.reset()
            laps.clear()
            refreshLaps()
            refreshPhaseLabel()
            refreshControlButtons()
        }
        findViewById<Button>(R.id.btnSaveRecord).setOnClickListener {
            val seconds = TimerEngine.displayMs / 1000
            if (seconds <= 0) {
                Toast.makeText(this, "还没有可保存的计时", Toast.LENGTH_SHORT).show()
                return@setOnClickListener
            }
            showNameDialog(seconds)
        }
        // 计次：记录当前累计时长（正计时 / 番茄钟可用）
        btnLap.setOnClickListener { addLap() }
        // 重复上次：还原上一次的模式与时长并立即开始
        btnRepeat.setOnClickListener { repeatLastTimer() }
        btnPomodoroSetting.setOnClickListener { showPomodoroDialog() }
        findViewById<Button>(R.id.btnClearLaps).setOnClickListener {
            laps.clear()
            refreshLaps()
        }
        findViewById<Button>(R.id.btnFloatToggle).setOnClickListener {
            toggleFloatBall()
        }
        findViewById<Button>(R.id.btnShare).setOnClickListener {
            showShareDialog()
        }
    }

    /** 记录一次计次：本段 = 当前累计 - 上次累计 */
    private fun addLap() {
        if (TimerEngine.mode == TimerEngine.MODE_COUNT_DOWN) {
            Toast.makeText(this, "倒计时模式不支持计次", Toast.LENGTH_SHORT).show()
            return
        }
        val total = TimerEngine.displayMs
        val prev = laps.lastOrNull()?.second ?: 0L
        if (total - prev < 1000L) {
            Toast.makeText(this, "至少间隔 1 秒再计次", Toast.LENGTH_SHORT).show()
            return
        }
        laps.add(Pair(total - prev, total))
        refreshLaps()
    }

    /** 刷新计次列表：只显示最近 10 条，最新的在最上面 */
    private fun refreshLaps() {
        layoutLaps.visibility = if (laps.isEmpty()) View.GONE else View.VISIBLE
        if (laps.isEmpty()) {
            tvLapList.text = ""
            return
        }
        val sb = StringBuilder()
        val from = maxOf(0, laps.size - 10)
        for (i in laps.size - 1 downTo from) {
            val seg = laps[i].first
            val total = laps[i].second
            sb.append("第 ${i + 1} 次   +${TimerEngine.format(seg)}   累计 ${TimerEngine.format(total)}\n")
        }
        tvLapList.text = sb.toString().trimEnd()
    }

    /** 记住本次计时参数，供「重复上次」使用 */
    private fun rememberLastTimer() {
        val secs = when (TimerEngine.mode) {
            TimerEngine.MODE_COUNT_DOWN -> TimerEngine.countdownTotalMs / 1000
            TimerEngine.MODE_POMODORO -> TimerEngine.pomodoroWorkMs / 1000
            else -> 0L
        }
        getSharedPreferences(PREFS, MODE_PRIVATE).edit()
            .putInt(KEY_LAST_MODE, TimerEngine.mode)
            .putLong(KEY_LAST_SECONDS, secs)
            .apply()
    }

    /** 重复上次计时：按上次模式与时长重置后立即开始 */
    private fun repeatLastTimer() {
        val prefs = getSharedPreferences(PREFS, MODE_PRIVATE)
        val mode = prefs.getInt(KEY_LAST_MODE, -1)
        if (mode < 0) {
            Toast.makeText(this, "还没有上次计时，先开始一次吧", Toast.LENGTH_SHORT).show()
            return
        }
        when (mode) {
            TimerEngine.MODE_COUNT_UP -> TimerEngine.setMode(TimerEngine.MODE_COUNT_UP)
            TimerEngine.MODE_COUNT_DOWN -> {
                TimerEngine.setMode(TimerEngine.MODE_COUNT_DOWN)
                val secs = prefs.getLong(KEY_LAST_SECONDS, TimerEngine.countdownTotalMs / 1000)
                TimerEngine.setCountdownSeconds(secs)
            }
            else -> TimerEngine.setMode(TimerEngine.MODE_POMODORO)
        }
        laps.clear()
        refreshModeUI()
        TimerEngine.start()
        refreshControlButtons()
        val tip = when (mode) {
            TimerEngine.MODE_COUNT_UP -> "已重复上次：正计时"
            TimerEngine.MODE_COUNT_DOWN -> "已重复上次：倒计时 " + TimerEngine.format(TimerEngine.countdownTotalMs)
            else -> "已重复上次：番茄钟"
        }
        Toast.makeText(this, "↻ $tip", Toast.LENGTH_SHORT).show()
    }

    private fun refreshControlButtons() {
        btnStartPause.text = if (TimerEngine.running) "⏸ 暂停" else "▶ 开始"
        // 停止按钮仅运行中 / 暂停中可用
        val canStop = TimerEngine.running || TimerEngine.isPausedMid()
        btnStop.isEnabled = canStop
        btnStop.alpha = if (canStop) 1f else 0.4f
        // 计次仅正计时 / 番茄钟运行中可用
        val canLap = TimerEngine.running && TimerEngine.mode != TimerEngine.MODE_COUNT_DOWN
        btnLap.isEnabled = canLap
        btnLap.alpha = if (canLap) 1f else 0.4f
    }

    /** 读取本地保存的番茄钟参数 */
    private fun loadPomodoroPrefs() {
        val prefs = getSharedPreferences(PREFS, MODE_PRIVATE)
        val work = prefs.getInt(KEY_POMO_WORK, 25).coerceIn(1, 600)
        val rest = prefs.getInt(KEY_POMO_BREAK, 5).coerceIn(1, 600)
        TimerEngine.setPomodoroMinutes(work, rest)
    }

    /** 番茄钟阶段切换：更新标签 + 语音播报 + 提示音 */
    private fun onPomodoroPhaseSwitch(toBreak: Boolean) {
        refreshPhaseLabel()
        playAlertTone()
        val minutes = if (toBreak) TimerEngine.pomodoroBreakMs / 60000
        else TimerEngine.pomodoroWorkMs / 60000
        if (toBreak) {
            speak("专注结束，休息 $minutes 分钟")
            Toast.makeText(this, "☕ 专注完成！休息 $minutes 分钟", Toast.LENGTH_LONG).show()
        } else {
            speak("休息结束，开始第 ${TimerEngine.pomodoroRound + 1} 轮专注")
            Toast.makeText(
                this, "🍅 休息结束，开始第 ${TimerEngine.pomodoroRound + 1} 轮专注（$minutes 分钟）",
                Toast.LENGTH_LONG
            ).show()
        }
        refreshControlButtons()
    }

    /**
     * 停止计时后的保存流程：
     * 本次已进行时长 > 1 秒时——
     * 「命名保存」开关开启：弹出命名对话框由用户自定义名称；
     * 开关关闭：自动保存，名称默认为当前时间（如"计时 10-29 17:05"）。
     */
    private fun offerSaveAfterStop(seconds: Long) {
        if (seconds <= 1) return
        val askName = getSharedPreferences(PREFS, MODE_PRIVATE)
            .getBoolean(KEY_ASK_NAME, true)
        if (askName) {
            showNameDialog(seconds)
        } else {
            saveRecord(defaultRecordName(), seconds)
        }
    }

    /** 自动保存时的默认记录名：当前时间，如"计时 10-29 17:05" */
    private fun defaultRecordName(): String =
        "计时 " + SimpleDateFormat("MM-dd HH:mm", Locale.CHINA).format(Date())

    private fun setupSwitch() {
        val prefs = getSharedPreferences(PREFS, MODE_PRIVATE)
        switchAskName.isChecked = prefs.getBoolean(KEY_ASK_NAME, true)
        switchAskName.setOnCheckedChangeListener { _, checked ->
            prefs.edit().putBoolean(KEY_ASK_NAME, checked).apply()
        }
    }

    /** 正计时到时提醒设置：分钟输入框 + 启用开关，改动即写入 SharedPreferences 并同步给引擎 */
    private fun setupAlertSetting() {
        val prefs = getSharedPreferences(PREFS, MODE_PRIVATE)
        val minutes = prefs.getInt(KEY_ALERT_MINUTES, 25)
        editAlertMinutes.setText(minutes.toString())
        switchAlert.isChecked = prefs.getBoolean(KEY_ALERT_ENABLED, false)
        applyAlertSetting()

        editAlertMinutes.addTextChangedListener(object : TextWatcher {
            override fun beforeTextChanged(s: CharSequence?, start: Int, count: Int, after: Int) {}
            override fun onTextChanged(s: CharSequence?, start: Int, before: Int, count: Int) {}
            override fun afterTextChanged(s: Editable?) {
                prefs.edit()
                    .putInt(KEY_ALERT_MINUTES, s?.toString()?.trim()?.toIntOrNull() ?: 0)
                    .apply()
                applyAlertSetting()
            }
        })
        switchAlert.setOnCheckedChangeListener { _, checked ->
            prefs.edit().putBoolean(KEY_ALERT_ENABLED, checked).apply()
            applyAlertSetting()
            if (checked && TimerEngine.alertMinutes <= 0) {
                Toast.makeText(this, "请先填写提醒分钟数", Toast.LENGTH_SHORT).show()
            }
        }
    }

    /** 把「开关 + 分钟数」合并后下发给 TimerEngine（开关关或分钟无效时为 0=关闭） */
    private fun applyAlertSetting() {
        val prefs = getSharedPreferences(PREFS, MODE_PRIVATE)
        val minutes = if (switchAlert.isChecked)
            prefs.getInt(KEY_ALERT_MINUTES, 0) else 0
        TimerEngine.setAlertMinutes(minutes)
    }

    /** 倒计时「结束前语音提醒」设置：开关 + 提前秒数（默认开启、3秒） */
    private fun setupPreAlertSetting() {
        val prefs = getSharedPreferences(PREFS, MODE_PRIVATE)
        editPreAlertSec.setText(prefs.getInt(KEY_PRE_ALERT_SEC, 3).toString())
        switchPreAlert.isChecked = prefs.getBoolean(KEY_PRE_ALERT_ENABLED, true)
        applyPreAlertSetting()

        editPreAlertSec.addTextChangedListener(object : TextWatcher {
            override fun beforeTextChanged(s: CharSequence?, start: Int, count: Int, after: Int) {}
            override fun onTextChanged(s: CharSequence?, start: Int, before: Int, count: Int) {}
            override fun afterTextChanged(s: Editable?) {
                val sec = s?.toString()?.trim()?.toIntOrNull() ?: 0
                prefs.edit().putInt(KEY_PRE_ALERT_SEC, sec).apply()
                applyPreAlertSetting()
            }
        })
        switchPreAlert.setOnCheckedChangeListener { _, checked ->
            prefs.edit().putBoolean(KEY_PRE_ALERT_ENABLED, checked).apply()
            applyPreAlertSetting()
            if (checked) {
                Toast.makeText(this, "已开启：倒计时剩余 ${editPreAlertSec.text} 秒时语音播报",
                    Toast.LENGTH_SHORT).show()
            }
        }
    }

    private fun applyPreAlertSetting() {
        val prefs = getSharedPreferences(PREFS, MODE_PRIVATE)
        val sec = prefs.getInt(KEY_PRE_ALERT_SEC, 3)
        TimerEngine.setPreAlert(switchPreAlert.isChecked, sec)
    }

    /** 倒计时进入设定剩余秒数：语音播报 + 短促提示音，计时不中断 */
    private fun onPreAlert(seconds: Int) {
        speak("还剩 $seconds 秒")
        playAlertTone()
    }

    /** 用系统 TTS 播报中文（初始化失败时静默跳过，不影响计时） */
    private fun speak(text: String) {
        if (!ttsReady) return
        try {
            tts?.speak(text, TextToSpeech.QUEUE_FLUSH, null, "floattimer_tts")
        } catch (_: Exception) {
        }
    }

    private fun initTts() {
        tts = TextToSpeech(this) { status ->
            if (status == TextToSpeech.SUCCESS) {
                try {
                    tts?.language = Locale.CHINA
                    ttsReady = true
                } catch (_: Exception) {
                }
            }
        }
    }

    /** 正计时到达设定分钟：播放提醒音 + Toast，仅触发一次，计时不中断 */
    private fun onCountUpAlert() {
        playAlertTone()
        Toast.makeText(this, "⏰ 到时提醒：设定时间已到！", Toast.LENGTH_LONG).show()
    }

    /** 用 ToneGenerator 播放短促提醒音（无需音频资源文件） */
    private fun playAlertTone() {
        try {
            val tg = ToneGenerator(AudioManager.STREAM_ALARM, 100)
            tg.startTone(ToneGenerator.TONE_CDMA_ALERT_CALL_GUARD, 600)
            handler.postDelayed({
                try {
                    tg.release()
                } catch (_: Exception) {
                }
            }, 700)
        } catch (_: Exception) {
        }
    }

    private fun setupRecords() {
        adapter = RecordAdapter(
            onEdit = { record -> showRenameDialog(record) },
            onLongClick = { record ->
                AlertDialog.Builder(this)
                    .setTitle("删除记录")
                    .setMessage("确定删除「${record.name}」这条计时记录吗？")
                    .setPositiveButton("删除") { _, _ ->
                        db.delete(record.id)
                        loadRecords()
                    }
                    .setNegativeButton("取消", null)
                    .show()
            }
        )
        val rv = findViewById<RecyclerView>(R.id.rvRecords)
        rv.layoutManager = LinearLayoutManager(this)
        rv.adapter = adapter
        findViewById<Button>(R.id.btnClearRecords).setOnClickListener {
            AlertDialog.Builder(this)
                .setTitle("清空记录")
                .setMessage("确定清空全部计时记录吗？此操作不可恢复。")
                .setPositiveButton("清空") { _, _ ->
                    db.clear()
                    loadRecords()
                }
                .setNegativeButton("取消", null)
                .show()
        }
        loadRecords()
    }

    private fun loadRecords() {
        val list = db.queryAll()
        adapter.submit(list)
        tvRecordEmpty.visibility = if (list.isEmpty()) View.VISIBLE else View.GONE
    }

    private fun setupPermissionBanner() {
        findViewById<Button>(R.id.btnGoPermission).setOnClickListener {
            startActivity(
                Intent(
                    Settings.ACTION_MANAGE_OVERLAY_PERMISSION,
                    Uri.parse("package:$packageName")
                )
            )
        }
    }

    /** 悬浮窗权限是否已具备：Android 6.0 以下没有权限管控，默认允许 */
    private fun canDrawOverlay(): Boolean =
        Build.VERSION.SDK_INT < Build.VERSION_CODES.M || Settings.canDrawOverlays(this)

    private fun refreshPermissionUI() {
        val granted = canDrawOverlay()
        layoutPermission.visibility = if (granted) View.GONE else View.VISIBLE
        findViewById<Button>(R.id.btnFloatToggle).text =
            if (FloatService.isRunning) "关闭悬浮球" else "开启悬浮球"
    }

    private fun toggleFloatBall() {
        if (FloatService.isRunning) {
            stopService(Intent(this, FloatService::class.java))
        } else {
            if (!canDrawOverlay()) {
                Toast.makeText(this, "请先开启悬浮窗权限", Toast.LENGTH_SHORT).show()
                startActivity(
                    Intent(
                        Settings.ACTION_MANAGE_OVERLAY_PERMISSION,
                        Uri.parse("package:$packageName")
                    )
                )
                return
            }
            val i = Intent(this, FloatService::class.java)
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) startForegroundService(i)
            else startService(i)
        }
        handler.postDelayed({ refreshPermissionUI() }, 300)
    }

    /** 倒计时自然结束回调 */
    private fun onTimerFinished() {
        refreshControlButtons()
        val seconds = TimerEngine.countdownTotalMs / 1000
        // 到时提醒：显式播放闹钟铃声（走闹钟音量通道，比通知音更响）+ 震动 + 语音播报
        AlarmPlayer.play(this)
        speak("时间到，计时结束")
        val askName = getSharedPreferences(PREFS, MODE_PRIVATE)
            .getBoolean(KEY_ASK_NAME, true)
        if (askName) {
            if (isForeground) {
                showNameDialog(seconds)
            } else {
                pendingFinishSeconds = seconds
                // 通过通知引导用户回到界面命名保存
                val i = Intent(this, MainActivity::class.java)
                i.putExtra(EXTRA_SHOW_NAME_DIALOG, true)
                i.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_SINGLE_TOP)
                startActivity(i)
            }
        } else {
            // 开关关闭：按当前时间自动保存
            saveRecord(defaultRecordName(), seconds)
        }
    }

    /** 弹出命名对话框，保存/跳过 */
    private fun showNameDialog(seconds: Long) {
        val view = layoutInflater.inflate(R.layout.dialog_name, null)
        val edit = view.findViewById<EditText>(R.id.editProjectName)
        AlertDialog.Builder(this)
            .setTitle("计时结束，给它起个名字吧")
            .setView(view)
            .setPositiveButton("保存") { _, _ ->
                val name = edit.text.toString().trim()
                    .ifEmpty { "未命名项目" }
                saveRecord(name, seconds)
            }
            .setNegativeButton("跳过") { _, _ ->
                saveRecord(defaultRecordName(), seconds)
            }
            .setCancelable(false)
            .show()
    }

    private fun saveRecord(name: String, seconds: Long) {
        db.insert(
            TimerRecord(
                0, name, TimerEngine.mode, seconds, System.currentTimeMillis()
            )
        )
        loadRecords()
        Toast.makeText(this, "已保存记录：$name", Toast.LENGTH_SHORT).show()
    }

    /** 记录重命名对话框：点记录条目「改名」按钮弹出，保存后更新 SQLite */
    private fun showRenameDialog(record: TimerRecord) {
        val view = layoutInflater.inflate(R.layout.dialog_name, null)
        val edit = view.findViewById<EditText>(R.id.editProjectName)
        edit.setText(record.name)
        edit.setSelection(record.name.length)
        AlertDialog.Builder(this)
            .setTitle("重命名记录")
            .setView(view)
            .setPositiveButton("保存") { _, _ ->
                val name = edit.text.toString().trim()
                if (name.isEmpty()) {
                    Toast.makeText(this, "名称不能为空", Toast.LENGTH_SHORT).show()
                    return@setPositiveButton
                }
                db.updateName(record.id, name)
                loadRecords()
                Toast.makeText(this, "已重命名为：$name", Toast.LENGTH_SHORT).show()
            }
            .setNegativeButton("取消", null)
            .show()
    }

    /** 分享有奖 · VIP尊享弹窗 */
    private fun showShareDialog() {
        // V2：邀请码不再固定，注册账号+实名认证后系统生成专属邀请码（ECJ开头）
        val regUrl = "https://ecojia.cn/login"

        // 构建内容
        val content = buildString {
            append("🏆 阶梯奖励 · 大使招募\n")
            append("● 邀请1人 → 推广大使 · 开盲盒\n")
            append("● 邀请5人 → 精英级大使 · 开盲盒\n")
            append("● 邀请10人 → 骨灰级大使 · 开盲盒\n")
            append("● 邀请20人 → 项目合伙人 · ¥999扫码加入\n")
            append("🎁 盲盒福利后期公布 · 满20人扫码支付¥999加入项目合伙人（利益详情咨询站长）\n")
            append("📌 新用户须通过你的推广链接或邀请码注册才计入你名下，否则算网站自然获客\n")
            append("🪪 注册账号后完成实名认证即可参与推广\n")
            append("👥 推广微信群二维码见官网 ecojia.cn 弹窗（后台统一设置）\n\n")
            append("👑 VIP专属权益\n")
            append("🌈 2027科技风专属主题皮肤\n")
            append("☁️ 计时数据云同步（多设备）\n")
            append("🔔 自定义提醒音效上传\n")
            append("📋 无限计次记录保存\n")
            append("📤 记录一键导出 Excel/PDF\n")
            append("📈 番茄钟专注效率统计图表\n\n")
            append("我的专属邀请码：注册实名后自动生成\n")
            append("🌐 www.ecojia.cn | 微信：xunijiayuan")
        }

        val dialog = AlertDialog.Builder(this)
            .setTitle("🎁 推广有惊喜 · 大使招募")
            .setMessage(content)
            .setPositiveButton("📋 复制注册入口") { _, _ ->
                val cm = getSystemService(CLIPBOARD_SERVICE) as android.content.ClipboardManager
                cm.setPrimaryClip(android.content.ClipData.newPlainText("注册入口", regUrl))
                Toast.makeText(this, "注册入口已复制，注册+实名后自动生成专属邀请码", Toast.LENGTH_LONG).show()
            }
            .setNeutralButton("🔗 复制分享文案") { _, _ ->
                val cm = getSystemService(CLIPBOARD_SERVICE) as android.content.ClipboardManager
                val shareText = "🎁 我在用「悬浮计时器」，2027科技风超好用！注册并完成实名认证即可获得你的专属邀请码，邀请好友双方都有奖励：\n$regUrl"
                cm.setPrimaryClip(android.content.ClipData.newPlainText("分享文案", shareText))
                Toast.makeText(this, "分享文案已复制，快去微信/QQ发给好友吧", Toast.LENGTH_SHORT).show()
            }
            .setNegativeButton("关闭", null)
            .create()
        dialog.show()

        // 美化消息文本
        dialog.findViewById<android.widget.TextView>(android.R.id.message)?.apply {
            setTextColor(0xFFE0E0F0.toInt())
            textSize = 13f
            setLineSpacing(4f, 1f)
        }
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        handleNameDialogIntent(intent)
        handleStopIntent(intent)
        handleShareIntent(intent)
    }

    /** 悬浮球菜单"分享有奖"拉起本界面时弹出分享弹窗 */
    private fun handleShareIntent(intent: Intent?) {
        if (intent?.getBooleanExtra(EXTRA_SHOW_SHARE_DIALOG, false) == true) {
            intent.removeExtra(EXTRA_SHOW_SHARE_DIALOG)
            showShareDialog()
        }
    }

    private fun handleNameDialogIntent(intent: Intent?) {
        if (intent?.getBooleanExtra(EXTRA_SHOW_NAME_DIALOG, false) == true) {
            intent.removeExtra(EXTRA_SHOW_NAME_DIALOG)
            val seconds = if (pendingFinishSeconds > 0) pendingFinishSeconds
            else TimerEngine.countdownTotalMs / 1000
            pendingFinishSeconds = -1
            showNameDialog(seconds)
        }
    }

    /** 悬浮球双击"停止"后拉起本界面：取出暂存秒数，走命名保存流程 */
    private fun handleStopIntent(intent: Intent?) {
        if (intent?.getBooleanExtra(EXTRA_SHOW_STOP_DIALOG, false) == true) {
            intent.removeExtra(EXTRA_SHOW_STOP_DIALOG)
            val seconds = pendingStopSeconds
            pendingStopSeconds = -1
            refreshControlButtons()
            offerSaveAfterStop(seconds)
        }
    }

    override fun onResume() {
        super.onResume()
        isForeground = true
        handler.post(clockLoop)
        refreshPermissionUI()
        refreshControlButtons()
        tvBigTime.text = TimerEngine.format(TimerEngine.displayMs)
        loadRecords()
        if (pendingFinishSeconds > 0) {
            showNameDialog(pendingFinishSeconds)
            pendingFinishSeconds = -1
        }
    }

    override fun onPause() {
        super.onPause()
        isForeground = false
        handler.removeCallbacks(clockLoop)
    }

    override fun onDestroy() {
        TimerEngine.removeListeners()
        TimerEngine.onAlert = null
        TimerEngine.onPreAlert = null
        AlarmPlayer.stop()
        try {
            tts?.stop()
            tts?.shutdown()
        } catch (_: Exception) {
        }
        tts = null
        ttsReady = false
        handler.removeCallbacks(clockLoop)
        try {
            unregisterReceiver(exitReceiver)
        } catch (_: Exception) {
        }
        super.onDestroy()
    }

    // ==================== 版本检查 ====================

    private fun checkUpdate() {
        Thread {
            try {
                val conn = URL(VERSION_CHECK_URL).openConnection() as HttpURLConnection
                conn.connectTimeout = 5000
                conn.readTimeout = 5000
                val json = JSONObject(conn.inputStream.bufferedReader().use { it.readText() })
                conn.disconnect()
                val android = json.optJSONObject("android") ?: return@Thread
                val latestCode = android.optInt("versionCode", 0)
                if (latestCode > BuildConfig.VERSION_CODE) {
                    val versionName = android.optString("versionName", "?")
                    val log = android.optString("updateLog", "")
                    val downloadUrl = android.optString("downloadUrl", "")
                    runOnUiThread { showUpdateDialog(versionName, log, downloadUrl) }
                }
            } catch (_: Exception) {
                // 网络异常静默处理
            }
        }.start()
    }

    private fun showUpdateDialog(versionName: String, log: String, downloadUrl: String) {
        AlertDialog.Builder(this)
            .setTitle("🎉 发现新版本 v$versionName")
            .setMessage(log)
            .setPositiveButton("立即下载") { _, _ -> downloadAndInstall(downloadUrl, versionName) }
            .setNegativeButton("稍后", null)
            .setCancelable(false)
            .show()
    }

    // ==================== 广告位（三端统一读取服务端 ad.json） ====================

    private fun loadAd() {
        Thread {
            try {
                val conn = URL(AD_CONFIG_URL).openConnection() as HttpURLConnection
                conn.connectTimeout = 6000
                conn.readTimeout = 6000
                val json = JSONObject(conn.inputStream.bufferedReader().use { it.readText() })
                conn.disconnect()
                if (!json.optBoolean("enabled", false)) return@Thread
                val video = json.optString("video", "")
                if (video.isBlank()) return@Thread
                val title = json.optString("title", "广告位招租")
                val advertiser = json.optString("advertiser", "广告位招租")
                val link = json.optString("link", "")
                val linkText = json.optString("linkText", "了解详情")
                runOnUiThread { showAdDialog(video, title, advertiser, link, linkText) }
            } catch (_: Exception) {
                // 网络异常静默处理，不打扰用户
            }
        }.start()
    }

    private fun showAdDialog(video: String, title: String, advertiser: String, link: String, linkText: String) {
        val view = layoutInflater.inflate(R.layout.dialog_ad, null)
        val textureView = view.findViewById<android.view.TextureView>(R.id.adVideo)
        view.findViewById<TextView>(R.id.adTitle).text = title
        view.findViewById<TextView>(R.id.adAdvertiser).text = "$advertiser · 联系微信 xunijiayuan"

        // 相对路径补齐为完整 URL
        val videoUrl = if (video.startsWith("http")) video
        else "https://ecojia.cn/timer/${video.trimStart('/')}"

        // 用 MediaPlayer + TextureView 播放：TextureView 走普通 View 的合成流程，
        // 在透明主题的对话框里也能正常出画面（VideoView 内部的 SurfaceView 在此时会“只出声不出画”）
        var player: android.media.MediaPlayer? = null
        fun releasePlayer() {
            try { player?.release() } catch (_: Exception) {}
            player = null
        }

        textureView.surfaceTextureListener = object : android.view.TextureView.SurfaceTextureListener {
            override fun onSurfaceTextureAvailable(surface: android.graphics.SurfaceTexture, width: Int, height: Int) {
                try {
                    val mp = android.media.MediaPlayer()
                    mp.setDataSource(videoUrl)
                    mp.setSurface(android.view.Surface(surface))
                    mp.setOnVideoSizeChangedListener { _, videoW, videoH ->
                        fitCenter(textureView, videoW, videoH)
                    }
                    mp.setOnPreparedListener { it.start() }
                    mp.prepareAsync()
                    player = mp
                } catch (_: Exception) {
                    // 播放失败静默处理，不影响计时器主功能
                }
            }

            override fun onSurfaceTextureSizeChanged(surface: android.graphics.SurfaceTexture, width: Int, height: Int) {}

            override fun onSurfaceTextureDestroyed(surface: android.graphics.SurfaceTexture): Boolean {
                releasePlayer()
                return true
            }

            override fun onSurfaceTextureUpdated(surface: android.graphics.SurfaceTexture) {}
        }

        val dialog = android.app.AlertDialog.Builder(this)
            .setView(view)
            .setCancelable(true)
            .create()
        dialog.window?.setBackgroundDrawableResource(android.R.color.transparent)
        dialog.setOnDismissListener { releasePlayer() }

        view.findViewById<View>(R.id.btnAdClose).setOnClickListener {
            releasePlayer()
            dialog.dismiss()
        }
        val btnLink = view.findViewById<Button>(R.id.btnAdLink)
        if (link.isNotBlank()) {
            btnLink.text = linkText
            btnLink.visibility = View.VISIBLE
            btnLink.setOnClickListener {
                startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(link)))
            }
        }
        dialog.show()
    }

    /** 按等比（不留黑边、不拉伸）居中显示视频画面 */
    private fun fitCenter(textureView: android.view.TextureView, videoW: Int, videoH: Int) {
        if (videoW <= 0 || videoH <= 0) return
        val viewW = textureView.width.toFloat()
        val viewH = textureView.height.toFloat()
        if (viewW <= 0f || viewH <= 0f) return
        val scale = minOf(viewW / videoW, viewH / videoH)
        val matrix = android.graphics.Matrix()
        matrix.setScale(
            (videoW * scale) / viewW,
            (videoH * scale) / viewH,
            viewW / 2f,
            viewH / 2f
        )
        textureView.setTransform(matrix)
    }

    private fun downloadAndInstall(url: String, versionName: String) {
        if (url.isBlank()) {
            Toast.makeText(this, "下载地址无效", Toast.LENGTH_SHORT).show()
            return
        }
        val request = DownloadManager.Request(Uri.parse(url)).apply {
            setTitle("悬浮计时器 v$versionName")
            setDescription("正在下载新版本...")
            setMimeType("application/vnd.android.package-archive")
            setNotificationVisibility(DownloadManager.Request.VISIBILITY_VISIBLE_NOTIFY_COMPLETED)
            setDestinationInExternalFilesDir(
                this@MainActivity,
                Environment.DIRECTORY_DOWNLOADS,
                "FloatTimer_update.apk"
            )
        }
        val dm = getSystemService(DOWNLOAD_SERVICE) as DownloadManager
        val downloadId = dm.enqueue(request)
        Toast.makeText(this, "开始下载新版本...", Toast.LENGTH_LONG).show()

        // 监听下载完成
        val receiver = object : BroadcastReceiver() {
            override fun onReceive(context: Context?, intent: Intent?) {
                if (intent?.getLongExtra(DownloadManager.EXTRA_DOWNLOAD_ID, -1) == downloadId) {
                    val file = File(
                        getExternalFilesDir(Environment.DIRECTORY_DOWNLOADS),
                        "FloatTimer_update.apk"
                    )
                    if (file.exists()) installApk(file)
                    unregisterReceiver(this)
                }
            }
        }
        ContextCompat.registerReceiver(
            this, receiver,
            IntentFilter(DownloadManager.ACTION_DOWNLOAD_COMPLETE),
            ContextCompat.RECEIVER_NOT_EXPORTED
        )
    }

    private fun installApk(file: File) {
        val uri = FileProvider.getUriForFile(
            this,
            "${packageName}.fileprovider",
            file
        )
        val intent = Intent(Intent.ACTION_VIEW).apply {
            setDataAndType(uri, "application/vnd.android.package-archive")
            addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
            addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        }
        startActivity(intent)
    }
}
