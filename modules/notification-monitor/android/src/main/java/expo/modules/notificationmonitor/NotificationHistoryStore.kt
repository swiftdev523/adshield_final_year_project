package expo.modules.notificationmonitor

import android.content.Context
import android.util.AtomicFile
import java.io.File
import java.io.OutputStreamWriter

internal class NotificationHistoryStore(context: Context) : NotificationRecordStore {
  private val atomicFile = AtomicFile(
    File(context.noBackupFilesDir, HISTORY_FILE_NAME),
  )

  override fun load(): NotificationRecordSnapshot {
    if (!atomicFile.baseFile.exists()) return NotificationRecordSnapshot(emptyList())

    val lines = atomicFile.openRead().bufferedReader(Charsets.UTF_8).useLines { sequence ->
      sequence.toList()
    }
    return NotificationRecordSnapshot(
      records = lines.mapNotNull(NotificationLineSerializer::deserialize),
      // Repository.loadPruned rewrites this snapshot through AtomicFile. The
      // rewritten v2 rows no longer contain any v1 notification body.
      requiresRewrite = lines.any(NotificationLineSerializer::isLegacyLine),
    )
  }

  override fun save(records: List<NotificationEventRecord>) {
    val output = atomicFile.startWrite()
    try {
      val writer = OutputStreamWriter(output, Charsets.UTF_8).buffered()
      records.forEach { record ->
        writer.write(NotificationLineSerializer.serialize(record))
        writer.newLine()
      }
      writer.flush()
      atomicFile.finishWrite(output)
    } catch (error: Exception) {
      atomicFile.failWrite(output)
      throw error
    }
  }

  override fun clear() {
    atomicFile.delete()
  }

  private companion object {
    const val HISTORY_FILE_NAME = "notification_history_v1.txt"
  }
}
