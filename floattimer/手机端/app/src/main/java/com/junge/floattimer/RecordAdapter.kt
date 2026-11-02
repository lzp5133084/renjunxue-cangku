package com.junge.floattimer

import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.TextView
import androidx.recyclerview.widget.RecyclerView
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

/** 使用记录列表适配器：「改名」按钮触发重命名回调，长按条目触发删除回调 */
class RecordAdapter(
    private val onEdit: (TimerRecord) -> Unit,
    private val onLongClick: (TimerRecord) -> Unit
) : RecyclerView.Adapter<RecordAdapter.VH>() {

    private val data = ArrayList<TimerRecord>()
    private val timeFormat = SimpleDateFormat("yyyy-MM-dd HH:mm:ss", Locale.CHINA)

    fun submit(list: List<TimerRecord>) {
        data.clear()
        data.addAll(list)
        notifyDataSetChanged()
    }

    class VH(v: View) : RecyclerView.ViewHolder(v) {
        val name: TextView = v.findViewById(R.id.tvRecordName)
        val detail: TextView = v.findViewById(R.id.tvRecordDetail)
        val btnEdit: View = v.findViewById(R.id.btnEditRecord)
    }

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): VH {
        val v = LayoutInflater.from(parent.context)
            .inflate(R.layout.item_record, parent, false)
        return VH(v)
    }

    override fun getItemCount() = data.size

    override fun onBindViewHolder(holder: VH, position: Int) {
        val r = data[position]
        holder.name.text = r.name
        val modeText = when (r.mode) {
            TimerEngine.MODE_COUNT_DOWN -> "倒计时"
            TimerEngine.MODE_POMODORO -> "番茄钟"
            else -> "正计时"
        }
        val dur = formatDuration(r.durationSeconds)
        holder.detail.text = "$modeText · 时长 $dur · ${timeFormat.format(Date(r.endTime))}"
        holder.btnEdit.setOnClickListener { onEdit(r) }
        holder.itemView.setOnLongClickListener {
            onLongClick(r)
            true
        }
    }

    private fun formatDuration(sec: Long): String {
        val h = sec / 3600
        val m = (sec % 3600) / 60
        val s = sec % 60
        return when {
            h > 0 -> "${h}小时${m}分${s}秒"
            m > 0 -> "${m}分${s}秒"
            else -> "${s}秒"
        }
    }
}
