package org.noisehanoi.mobile

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test
import org.noisehanoi.mobile.form.Answers
import org.noisehanoi.mobile.form.Attachment
import org.noisehanoi.mobile.form.GeoPoint
import org.noisehanoi.mobile.form.NOISE_FORM_V2
import org.noisehanoi.mobile.form.NOISE_FORM_V3_VERSION
import org.noisehanoi.mobile.form.PUBLIC_COLLECTOR
import org.noisehanoi.mobile.form.normaliseNumber
import org.noisehanoi.mobile.odk.InstanceXml

class InstanceXmlTest {

    private fun filled() = Answers(NOISE_FORM_V2)
        .with("site", "ocean_park")
        .with("collector", "lucas")
        .withGeoPoint("location", GeoPoint(20.9922001, 105.9442618, 12.0, 4.9))
        .withAttachment(Attachment("audio_sample", "audio_1.m4a", "/tmp/audio_1.m4a"))
        .with("noise_db", "75.0")
        .with("noise_class", "transportation")
        .with("dist_to_road", "d_0_2")

    @Test
    fun `instance carries the deployed form id and version`() {
        val xml = InstanceXml.build(filled(), "uuid:abc", "S", "E")
        assertTrue(xml.contains("<hanoi_noise_v1 id=\"hanoi_noise_v1\" version=\"2026061204\">"))
        assertTrue(xml.trimEnd().endsWith("</hanoi_noise_v1>"))
    }

    @Test
    fun `geopoint uses the ODK lat lon alt accuracy form`() {
        val xml = InstanceXml.build(filled(), "uuid:abc", "S", "E")
        assertTrue(xml.contains("<location>20.9922001 105.9442618 12.0 4.9</location>"))
    }

    @Test
    fun `attachment is referenced by file name, not by path`() {
        val xml = InstanceXml.build(filled(), "uuid:abc", "S", "E")
        assertTrue(xml.contains("<audio_sample>audio_1.m4a</audio_sample>"))
        assertFalse(xml.contains("/tmp/"))
    }

    @Test
    fun `unanswered optional questions produce no element`() {
        val xml = InstanceXml.build(filled(), "uuid:abc", "S", "E")
        assertFalse(xml.contains("<count_cars>"))
        assertFalse(xml.contains("<note>"))
    }

    @Test
    fun `extra fields are omitted unless the extended form is in use`() {
        val plain = InstanceXml.build(filled(), "uuid:abc", "S", "E")
        assertFalse(plain.contains("app_noise_db"))
        val extended = InstanceXml.build(
            filled(), "uuid:abc", "S", "E",
            extraFields = mapOf("app_noise_db" to "71.4", "device_model" to "Google Pixel 8"),
        )
        assertTrue(extended.contains("<app_noise_db>71.4</app_noise_db>"))
    }

    /**
     * Kobo replaces the XLSForm's `id_string` on deployment with the asset's own
     * identifier. An instance built from the spreadsheet names a form the server
     * has never heard of, and is answered 404 — one submission at a time, in the
     * field, indistinguishable from a wrong URL. This is the defect that made the
     * first real submission fail.
     */
    @Test
    fun `the instance names the form as the server deployed it`() {
        val xml = InstanceXml.build(
            filled(), "uuid:abc", "S", "E",
            deployment = InstanceXml.Deployment(
                formId = "aA8FaTuUVSkRjbUW7rCBz7",
                version = "4 (2026-08-20 10:07:19)",
            ),
        )
        assertTrue(xml.contains("<aA8FaTuUVSkRjbUW7rCBz7 id=\"aA8FaTuUVSkRjbUW7rCBz7\""))
        assertTrue(xml.contains("version=\"4 (2026-08-20 10:07:19)\""))
        assertTrue(xml.trimEnd().endsWith("</aA8FaTuUVSkRjbUW7rCBz7>"))
        assertFalse(xml.contains("hanoi_noise_v1"))
    }

    /** With nothing fetched, it falls back to the spreadsheet's own identifiers. */
    @Test
    fun `without a deployment the instance uses the form spec`() {
        val xml = InstanceXml.build(filled(), "uuid:abc", "S", "E")
        assertTrue(xml.contains("<hanoi_noise_v1 id=\"hanoi_noise_v1\" version=\"2026061204\">"))
    }

    /** The list is a short flat document; parsing it must not need a device. */
    @Test
    fun `the form list is parsed into ids, names and versions`() {
        val xml = """
            <?xml version="1.0" encoding="utf-8"?>
            <xforms xmlns="http://openrosa.org/xforms/xformsList">
              <xform>
                <formID>aA8FaTuUVSkRjbUW7rCBz7</formID>
                <name>Hanoi Urban Noise Survey</name>
                <version>4 (2026-08-20 10:07:19)</version>
                <downloadUrl>https://kc.kobotoolbox.org/lucasz/forms/3768922/form.xml</downloadUrl>
              </xform>
            </xforms>
        """.trimIndent()
        val forms = org.noisehanoi.mobile.odk.OpenRosaClient.parseFormList(xml)
        assertEquals(1, forms.size)
        assertEquals("aA8FaTuUVSkRjbUW7rCBz7", forms[0].formId)
        assertEquals("Hanoi Urban Noise Survey", forms[0].name)
        assertEquals("4 (2026-08-20 10:07:19)", forms[0].version)
    }

    @Test
    fun `text is escaped, so a note cannot break the document`() {
        val answers = filled().with("note", "horn burst <loud> & \"sudden\"")
        val xml = InstanceXml.build(answers, "uuid:abc", "S", "E")
        assertTrue(xml.contains("<note>horn burst &lt;loud&gt; &amp; &quot;sudden&quot;</note>"))
    }

    @Test
    fun `timestamp is ISO-8601 with milliseconds and an explicit offset`() {
        // 2026-06-10T14:33:42.770+07:00 — the first row of measurements.csv, Hanoi time.
        val millis = 1_781_076_822_770L
        assertEquals("2026-06-10T14:33:42.770+07:00", InstanceXml.timestamp(millis, 7 * 60))
    }

    @Test
    fun `validation follows the XLSForm constraints`() {
        assertTrue(filled().problems().isEmpty())
        assertEquals(
            "Must be between 20 and 120",
            filled().with("noise_db", "130").problems()["noise_db"],
        )
        assertEquals(
            "Must be between 0 and 500",
            filled().with("count_cars", "900").problems()["count_cars"],
        )
        assertEquals("Unknown choice", filled().with("site", "nowhere").problems()["site"])
    }

    @Test
    fun `a missing required answer is reported`() {
        assertEquals("Required", filled().with("noise_class", null).problems()["noise_class"])
    }

    /**
     * A French or Vietnamese keyboard offers a decimal comma, and the XLSForm
     * constraint is 20..120. Left alone, "72,5" parses as nothing and the field
     * reads "Not a number" at the one moment the user is standing in traffic.
     */
    @Test
    fun `a decimal comma is accepted and written as a point`() {
        val answers = filled().with("noise_db", normaliseNumber("72,5"))
        assertTrue(answers.problems().isEmpty())
        assertTrue(InstanceXml.build(answers, "uuid:abc", "S", "E").contains("<noise_db>72.5</noise_db>"))
    }

    /**
     * A public contributor is a real value of `collector`, not an empty one.
     * `01_prepare_field_data.py` keys de-duplication on that column and maps its
     * per-collector calibration offset through it; blanking it for strangers
     * would silently merge every public submission into one collector.
     */
    @Test
    fun `the public collector is a choice the form accepts`() {
        val answers = filled().with("collector", PUBLIC_COLLECTOR)
        assertTrue(answers.problems().isEmpty())
        assertTrue(
            InstanceXml.build(answers, "uuid:abc", "S", "E")
                .contains("<collector>public</collector>")
        )
    }

    /** Re-measuring replaces the clip, and the instance must name only the new one. */
    @Test
    fun `a replaced attachment leaves no trace in the instance`() {
        val answers = filled()
            .withAttachment(Attachment("audio_sample", "audio_2.m4a", "/tmp/audio_2.m4a"))
        val xml = InstanceXml.build(answers, "uuid:abc", "S", "E")
        assertTrue(xml.contains("<audio_sample>audio_2.m4a</audio_sample>"))
        assertFalse(xml.contains("audio_1.m4a"))
    }
}
