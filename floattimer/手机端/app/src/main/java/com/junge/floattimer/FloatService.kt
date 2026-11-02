package com.junge.floattimer

import android.animation.ValueAnimator
import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Intent
import android.graphics.PixelFormat
import android.os.Build
import android.os.Handler
import android.os.IBinder
import android.os.Looper
import android.view.Gravity
import android.view.LayoutInflater
import android.view.MotionEvent
import android.view.View
import android.view.WindowManager
import android.view.animation.DecelerateInterpolator
import android.widget.TextView
import android.widget.Toast
import kotlin.math.abs

/**
 * 悬浮球前台服务：72dp 圆形靛紫渐变球，显示计时 mm:ss。
 * 可拖动，松手自动吸附左右边缘；
 * 单击（延迟300ms判定）回到主界面，双击开始/停止计时，长按弹出功能菜单。
 */
class FloatService : Service() {

    companion object {
        const val CHANNEL_ID = "float_timer_channel"
        const val NOTIFY_ID = 1001
        const val ACTION_STOP = "com.junge.floattimer.STOP_FLOAT"

        @Volatile
        var isRunning = false
            private set
    }

    private lateinit var wm: WindowManager
    private var floatView: View? = null
    /** 长按菜单视图（同一时刻只允许存在一个） */
    private var menuView: View? = null
    private var tvTime: TextView? = null
    private lateinit var params: WindowManager.LayoutParams
    private val handler = Handler(Looper.getMainLooper())

    private var lastDisplayMs = -1L

    private val refreshLoop = object : Runnable {
        override fun run() {
            val ms = TimerEngine.displayMs
            tvTime?.text = TimerEngine.formatShort(ms)
            // 后台检测倒计时自然结束：通知用户回来命名保存
            if (TimerEngine.mode == TimerEngine.MODE_COUNT_DOWN
                && lastDisplayMs > 0 && ms == 0L
                && !TimerEngine.running && !MainActivity.isForeground
            ) {
                notifyTimerFinished()
            }
            lastDisplayMs = ms
            handler.postDelayed(this, 200)
        }
    }

    private fun notifyTimerFinished() {
        // 后台结束时同样用闹钟铃声 + 震动，避免只有通知音听不到
        AlarmPlayer.play(this)
        val nm = getSystemService(NOTIFICATION_SERVICE) as NotificationManager
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            nm.createNotificationChannel(
                NotificationChannel(
                    CHANNEL_ID + "_finish", "计时结束提醒", NotificationManager.IMPORTANCE_HIGH
                )
            )
        }
        val openIntent = PendingIntent.getActivity(
            this, 1,
            Intent(this, MainActivity::class.java).apply {
                putExtra(MainActivity.EXTRA_SHOW_NAME_DIALOG, true)
                addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_SINGLE_TOP)
            },
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )
        val builder = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O)
            Notification.Builder(this, CHANNEL_ID + "_finish") else Notification.Builder(this)
        nm.notify(
            NOTIFY_ID + 1, builder
                .setContentTitle("计时结束")
                .setContentText("点击为这次计时命名并保存记录")
                .setSmallIcon(R.drawable.ic_launcher_foreground)
                .setContentIntent(openIntent)
                .setAutoCancel(true)
                .build()
        )
    }

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onCreate() {
        super.onCreate()
        isRunning = true
        wm = getSystemService(WINDOW_SERVICE) as WindowManager
        startForegroundWithNotification()
        showFloatBall()
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        if (intent?.action == ACTION_STOP) {
            stopSelf()
            return START_NOT_STICKY
        }
        return START_STICKY
    }

    private fun startForegroundWithNotification() {
        val nm = getSystemService(NOTIFICATION_SERVICE) as NotificationManager
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            nm.createNotificationChannel(
                NotificationChannel(CHANNEL_ID, "悬浮计时球", NotificationManager.IMPORTANCE_LOW)
            )
        }
        val openIntent = PendingIntent.getActivity(
            this, 0,
            Intent(this, MainActivity::class.java),
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )
        val builder = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O)
            Notification.Builder(this, CHANNEL_ID) else Notification.Builder(this)
        val notification = builder
            .setContentTitle("军哥懂保·悬浮计时器")
            .setContentText("悬浮球运行中，点击返回主界面")
            .setSmallIcon(R.drawable.ic_launcher_foreground)
            .setContentIntent(openIntent)
            .setOngoing(true)
            .build()
        startForeground(NOTIFY_ID, notification)
    }

    private fun showFloatBall() {
        floatView = LayoutInflater.from(this).inflate(R.layout.float_ball, null)
        tvTime = floatView?.findViewById(R.id.tvFloatTime)
        tvTime?.text = TimerEngine.formatShort(TimerEngine.displayMs)

        val type = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O)
            WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY
        else WindowManager.LayoutParams.TYPE_PHONE

        val size = dp(72)
        params = WindowManager.LayoutParams(
            size, size, type,
            WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE,
            PixelFormat.TRANSLUCENT
        )
        params.gravity = Gravity.TOP or Gravity.START
        params.x = 0
        params.y = dp(200)

        attachTouch(floatView!!)
        wm.addView(floatView, params)
        handler.post(refreshLoop)
    }

    /** 单击延迟判定时长（毫秒）：等待期间若出现第二次点击则判定为双击 */
    private val clickDelayMs = 300L

    /** 长按触发时长（毫秒） */
    private val longPressMs = 500L

    private var clickRunnable: Runnable? = null
    private var longPressRunnable: Runnable? = null
    private var longPressTriggered = false

    private fun attachTouch(view: View) {
        var downRawX = 0f
        var downRawY = 0f
        var downX = 0
        var downY = 0
        var moved = false

        view.setOnTouchListener { _, event ->
            when (event.action) {
                MotionEvent.ACTION_DOWN -> {
                    downRawX = event.rawX
                    downRawY = event.rawY
                    downX = params.x
                    downY = params.y
                    moved = false
                    longPressTriggered = false
                    // 启动长按计时：按住不动 500ms 弹出功能菜单
                    cancelLongPress()
                    longPressRunnable = Runnable {
                        if (!moved) {
                            longPressTriggered = true
                            // 长按生效时取消等待中的单击，避免菜单弹出后又误跳主界面
                            cancelPendingClick()
                            showMenu()
                        }
                    }
                    handler.postDelayed(longPressRunnable!!, longPressMs)
                    true
                }
                MotionEvent.ACTION_MOVE -> {
                    val dx = event.rawX - downRawX
                    val dy = event.rawY - downRawY
                    if (!moved && (abs(dx) > dp(6) || abs(dy) > dp(6))) {
                        moved = true
                        // 一旦开始拖动，取消长按与等待中的单击
                        cancelLongPress()
                        cancelPendingClick()
                    }
                    if (moved) {
                        params.x = downX + dx.toInt()
                        params.y = downY + dy.toInt()
                        try {
                            wm.updateViewLayout(view, params)
                        } catch (_: Exception) {
                        }
                    }
                    true
                }
                MotionEvent.ACTION_UP -> {
                    cancelLongPress()
                    when {
                        moved -> {
                            cancelPendingClick()
                            snapToEdge()
                        }
                        longPressTriggered -> {
                            // 长按已处理，不再响应单击
                        }
                        clickRunnable != null -> {
                            // 300ms 内第二次抬起：判定为双击
                            cancelPendingClick()
                            onDoubleTap()
                        }
                        else -> {
                            // 单击：延迟 300ms 执行，等待是否双击
                            clickRunnable = Runnable {
                                clickRunnable = null
                                openMainActivity()
                            }
                            handler.postDelayed(clickRunnable!!, clickDelayMs)
                        }
                    }
                    true
                }
                MotionEvent.ACTION_CANCEL -> {
                    cancelLongPress()
                    true
                }
                else -> false
            }
        }
    }

    private fun cancelPendingClick() {
        clickRunnable?.let { handler.removeCallbacks(it) }
        clickRunnable = null
    }

    private fun cancelLongPress() {
        longPressRunnable?.let { handler.removeCallbacks(it) }
        longPressRunnable = null
    }

    /** 单击：展开主界面 */
    private fun openMainActivity() {
        val i = Intent(this, MainActivity::class.java)
        i.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_SINGLE_TOP)
        startActivity(i)
    }

    /**
     * 双击：开始 / 停止计时。
     * 未在运行（初始状态或已自然结束）→ 开始；
     * 运行中或暂停中 → 停止，并把本次秒数交给主界面走命名保存流程。
     */
    private fun onDoubleTap() {
        if (TimerEngine.running || TimerEngine.isPausedMid()) {
            MainActivity.pendingStopSeconds = TimerEngine.stop()
            val i = Intent(this, MainActivity::class.java)
            i.putExtra(MainActivity.EXTRA_SHOW_STOP_DIALOG, true)
            i.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_SINGLE_TOP)
            startActivity(i)
        } else {
            TimerEngine.start()
        }
    }

    /**
     * 长按：弹出功能菜单。
     * 说明：Service 中使用 AppCompat 的 AlertDialog 会因缺少 AppCompat 主题直接崩溃
     * （AndroidRuntimeException: You need to use a Theme.AppCompat theme），
     * 因此改为用 WindowManager 挂载自绘的悬浮菜单卡片，样式与网页端右键菜单一致。
     */
    private fun showMenu() {
        if (menuView != null) return
        val view = LayoutInflater.from(this).inflate(R.layout.float_menu, null)
        val lp = WindowManager.LayoutParams(
            WindowManager.LayoutParams.MATCH_PARENT,
            WindowManager.LayoutParams.MATCH_PARENT,
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O)
                WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY
            else
                @Suppress("DEPRECATION") WindowManager.LayoutParams.TYPE_PHONE,
            WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE,
            PixelFormat.TRANSLUCENT
        )
        // 点击卡片外空白处关闭菜单
        view.findViewById<View>(R.id.menuRoot).setOnClickListener { dismissMenu() }
        // 卡片本体吞掉点击，避免误关
        view.findViewById<View>(R.id.menuCard).setOnClickListener { }

        (view.findViewById<TextView>(R.id.menuStartPause)).text =
            if (TimerEngine.running) "⏸ 暂停计时" else "▶ 开始计时"

        view.findViewById<View>(R.id.menuOpen).setOnClickListener {
            dismissMenu(); openMainActivity()
        }
        view.findViewById<View>(R.id.menuStartPause).setOnClickListener {
            dismissMenu()
            if (TimerEngine.running) TimerEngine.pause() else TimerEngine.start()
        }
        view.findViewById<View>(R.id.menuRepeat).setOnClickListener {
            dismissMenu()
            // 重复计时：按当前模式和预设重置并立即开始新一轮
            TimerEngine.reset()
            TimerEngine.start()
            Toast.makeText(this, "已按当前模式重新开始计时", Toast.LENGTH_SHORT).show()
        }
        view.findViewById<View>(R.id.menuShare).setOnClickListener {
            dismissMenu()
            val i = Intent(this, MainActivity::class.java).apply {
                addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_SINGLE_TOP)
                putExtra(MainActivity.EXTRA_SHOW_SHARE_DIALOG, true)
            }
            startActivity(i)
        }
        view.findViewById<View>(R.id.menuHide).setOnClickListener {
            dismissMenu()
            // 隐藏界面：回到桌面，悬浮球保留在屏幕上
            val i = Intent(Intent.ACTION_MAIN)
            i.addCategory(Intent.CATEGORY_HOME)
            i.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            startActivity(i)
        }
        view.findViewById<View>(R.id.menuExit).setOnClickListener {
            dismissMenu()
            // 退出程序：关闭主界面并停止悬浮球服务
            sendBroadcast(Intent(MainActivity.ACTION_EXIT_APP).setPackage(packageName))
            stopSelf()
        }

        try {
            wm.addView(view, lp)
            menuView = view
        } catch (e: Exception) {
            Toast.makeText(this, "菜单打开失败：${e.message}", Toast.LENGTH_SHORT).show()
        }
    }

    /** 关闭长按菜单（幂等，服务销毁时也会调用） */
    private fun dismissMenu() {
        val v = menuView ?: return
        menuView = null
        try {
            wm.removeView(v)
        } catch (_: Exception) {
        }
    }

    /** 松手后吸附到距离较近的一侧屏幕边缘 */
    private fun snapToEdge() {
        val screenW = resources.displayMetrics.widthPixels
        val targetX = if (params.x + dp(36) <= screenW / 2) 0 else screenW - dp(72)
        val animator = ValueAnimator.ofInt(params.x, targetX)
        animator.duration = 250
        animator.interpolator = DecelerateInterpolator()
        animator.addUpdateListener { a ->
            params.x = a.animatedValue as Int
            try {
                floatView?.let { wm.updateViewLayout(it, params) }
            } catch (_: Exception) {
            }
        }
        animator.start()
    }

    private fun dp(v: Int): Int = (v * resources.displayMetrics.density).toInt()

    override fun onDestroy() {
        isRunning = false
        handler.removeCallbacks(refreshLoop)
        cancelPendingClick()
        cancelLongPress()
        dismissMenu()
        floatView?.let {
            try {
                wm.removeView(it)
            } catch (_: Exception) {
            }
        }
        floatView = null
        super.onDestroy()
    }
}
