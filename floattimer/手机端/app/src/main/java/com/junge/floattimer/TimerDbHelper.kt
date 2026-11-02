package com.junge.floattimer

import android.content.ContentValues
import android.content.Context
import android.database.sqlite.SQLiteDatabase
import android.database.sqlite.SQLiteOpenHelper

/** 计时记录实体 */
data class TimerRecord(
    val id: Long,
    val name: String,
    val mode: Int,
    val durationSeconds: Long,
    val endTime: Long
)

/**
 * 使用记录数据库（SQLiteOpenHelper 手写实现，替代 Room，降低构建依赖风险）
 */
class TimerDbHelper(context: Context) :
    SQLiteOpenHelper(context, "float_timer.db", null, 1) {

    companion object {
        const val TABLE = "timer_record"
    }

    override fun onCreate(db: SQLiteDatabase) {
        db.execSQL(
            """CREATE TABLE $TABLE(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                mode INTEGER NOT NULL,
                durationSeconds INTEGER NOT NULL,
                endTime INTEGER NOT NULL
            )"""
        )
    }

    override fun onUpgrade(db: SQLiteDatabase, oldVersion: Int, newVersion: Int) {
        db.execSQL("DROP TABLE IF EXISTS $TABLE")
        onCreate(db)
    }

    fun insert(record: TimerRecord): Long {
        val v = ContentValues().apply {
            put("name", record.name)
            put("mode", record.mode)
            put("durationSeconds", record.durationSeconds)
            put("endTime", record.endTime)
        }
        return writableDatabase.insert(TABLE, null, v)
    }

    fun queryAll(): List<TimerRecord> {
        val list = ArrayList<TimerRecord>()
        readableDatabase.rawQuery(
            "SELECT id,name,mode,durationSeconds,endTime FROM $TABLE ORDER BY endTime DESC",
            null
        ).use { c ->
            while (c.moveToNext()) {
                list.add(
                    TimerRecord(
                        c.getLong(0), c.getString(1), c.getInt(2),
                        c.getLong(3), c.getLong(4)
                    )
                )
            }
        }
        return list
    }

    fun delete(id: Long) {
        writableDatabase.delete(TABLE, "id=?", arrayOf(id.toString()))
    }

    /** 重命名记录 */
    fun updateName(id: Long, name: String) {
        val v = ContentValues().apply { put("name", name) }
        writableDatabase.update(TABLE, v, "id=?", arrayOf(id.toString()))
    }

    fun clear() {
        writableDatabase.execSQL("DELETE FROM $TABLE")
    }

    fun count(): Int {
        readableDatabase.rawQuery("SELECT COUNT(*) FROM $TABLE", null).use { c ->
            return if (c.moveToFirst()) c.getInt(0) else 0
        }
    }
}
