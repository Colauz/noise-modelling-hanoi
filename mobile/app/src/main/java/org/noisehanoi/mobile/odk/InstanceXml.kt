package org.noisehanoi.mobile.odk

import org.noisehanoi.mobile.form.Answers
import java.util.Locale

/**
 * Builds the ODK/XForm instance document that goes into the `xml_submission_file`
 * part of an OpenRosa submission.
 *
 * Shape, which KoBoCAT validates against the deployed form:
 *
 * ```xml
 * <hanoi_noise_v1 id="hanoi_noise_v1" version="2026061204">
 *   <start>2026-08-19T20:31:07.412+07:00</start>
 *   ...
 *   <meta><instanceID>uuid:2f1c...</instanceID></meta>
 * </hanoi_noise_v1>
 * ```
 *
 * Written with a StringBuilder rather than `android.util.Xml` so that it stays a
 * pure-Kotlin function and can be unit-tested on the JVM without an emulator.
 */
object InstanceXml {

    /** What the server assigned to a form when it was deployed. */
    data class Deployment(val formId: String, val version: String)

    /**
     * @param extraFields appended after the form's own fields, in order. Used for
     *   the app-measured level and device metadata, which only exist on a v3 form
     *   — see `APP_EXTENSION_FIELDS`. Empty when submitting to the deployed v2.
     * @param deployment the identifiers the server assigned when the form was
     *   deployed. Kobo replaces the XLSForm's `id_string` with the asset's own
     *   identifier, so an instance built from the spreadsheet names a form the
     *   server has never heard of and is answered 404. Null falls back to the
     *   spec's own id and version, which is right only for a server that kept
     *   them.
     */
    fun build(
        answers: Answers,
        instanceId: String,
        start: String,
        end: String,
        extraFields: Map<String, String> = emptyMap(),
        deployment: Deployment? = null,
    ): String {
        val spec = answers.spec
        val values = answers.values
        val root = deployment?.formId ?: spec.id
        val version = deployment?.version ?: spec.version
        val sb = StringBuilder(1024)
        sb.append("<?xml version='1.0' encoding='UTF-8' ?>\n")
        sb.append("<").append(root)
            .append(" id=\"").append(esc(root)).append("\"")
            .append(" version=\"").append(esc(version)).append("\">\n")

        // `start` and `end` are the XLSForm metadata questions of both forms.
        element(sb, "start", start)
        element(sb, "end", end)
        for (q in spec.questions) {
            val v = values[q.name] ?: continue
            element(sb, q.name, v)
        }
        for ((name, v) in extraFields) {
            if (v.isNotBlank()) element(sb, name, v)
        }
        sb.append("  <meta>\n    <instanceID>").append(esc(instanceId))
            .append("</instanceID>\n  </meta>\n")
        sb.append("</").append(root).append(">\n")
        return sb.toString()
    }

    /** `uuid:` prefix is what ODK Collect writes and what deduplication keys on. */
    fun newInstanceId(): String = "uuid:" + java.util.UUID.randomUUID().toString()

    /** ODK timestamps are ISO-8601 with milliseconds and an explicit offset. */
    fun timestamp(millis: Long, offsetMinutes: Int): String {
        val cal = java.util.Calendar.getInstance(
            java.util.TimeZone.getTimeZone(offsetToZoneId(offsetMinutes)), Locale.US,
        )
        cal.timeInMillis = millis
        val sign = if (offsetMinutes < 0) '-' else '+'
        val abs = kotlin.math.abs(offsetMinutes)
        return String.format(
            Locale.US, "%04d-%02d-%02dT%02d:%02d:%02d.%03d%c%02d:%02d",
            cal.get(java.util.Calendar.YEAR),
            cal.get(java.util.Calendar.MONTH) + 1,
            cal.get(java.util.Calendar.DAY_OF_MONTH),
            cal.get(java.util.Calendar.HOUR_OF_DAY),
            cal.get(java.util.Calendar.MINUTE),
            cal.get(java.util.Calendar.SECOND),
            cal.get(java.util.Calendar.MILLISECOND),
            sign, abs / 60, abs % 60,
        )
    }

    private fun offsetToZoneId(offsetMinutes: Int): String {
        val sign = if (offsetMinutes < 0) "-" else "+"
        val abs = kotlin.math.abs(offsetMinutes)
        return String.format(Locale.US, "GMT%s%02d:%02d", sign, abs / 60, abs % 60)
    }

    private fun element(sb: StringBuilder, name: String, value: String) {
        sb.append("  <").append(name).append(">")
            .append(esc(value))
            .append("</").append(name).append(">\n")
    }

    private fun esc(s: String): String {
        val sb = StringBuilder(s.length + 16)
        for (c in s) when (c) {
            '&' -> sb.append("&amp;")
            '<' -> sb.append("&lt;")
            '>' -> sb.append("&gt;")
            '"' -> sb.append("&quot;")
            '\'' -> sb.append("&apos;")
            else -> sb.append(c)
        }
        return sb.toString()
    }
}
