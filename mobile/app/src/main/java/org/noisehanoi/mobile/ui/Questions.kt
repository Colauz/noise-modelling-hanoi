package org.noisehanoi.mobile.ui

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.FilterChip
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import org.noisehanoi.mobile.form.DecimalQ
import org.noisehanoi.mobile.form.IntegerQ
import org.noisehanoi.mobile.form.Question
import org.noisehanoi.mobile.form.SelectOneQ
import org.noisehanoi.mobile.form.TextQ

@Composable
fun QuestionLabel(
    question: Question,
    problem: String?,
    labelOverride: String? = null,
    hintOverride: String? = null,
) {
    Column {
        Text(
            text = (labelOverride ?: question.label) + if (question.required) " *" else "",
            style = MaterialTheme.typography.titleSmall,
        )
        (hintOverride ?: question.hint)?.let {
            Text(it, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.outline)
        }
        problem?.let {
            Text(it, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.error)
        }
    }
}

@OptIn(ExperimentalLayoutApi::class)
@Composable
fun SelectOneField(question: SelectOneQ, value: String?, problem: String?, onChange: (String?) -> Unit) {
    Column(Modifier.fillMaxWidth().padding(vertical = 8.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
        QuestionLabel(question, problem)
        FlowRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            question.choices.forEach { choice ->
                FilterChip(
                    selected = value == choice.name,
                    onClick = { onChange(if (value == choice.name) null else choice.name) },
                    label = { Text(choice.label) },
                )
            }
        }
    }
}

@Composable
fun NumberField(
    question: Question,
    value: String?,
    problem: String?,
    decimal: Boolean,
    labelOverride: String? = null,
    hintOverride: String? = null,
    onChange: (String) -> Unit,
) {
    Column(Modifier.fillMaxWidth().padding(vertical = 8.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
        QuestionLabel(question, problem, labelOverride, hintOverride)
        OutlinedTextField(
            value = value.orEmpty(),
            onValueChange = onChange,
            singleLine = true,
            isError = problem != null,
            keyboardOptions = KeyboardOptions(
                keyboardType = if (decimal) KeyboardType.Decimal else KeyboardType.Number,
            ),
            supportingText = {
                val range = when (question) {
                    is DecimalQ -> "${question.min} – ${question.max}"
                    is IntegerQ -> "${question.min} – ${question.max}"
                    else -> null
                }
                range?.let { Text(it) }
            },
            modifier = Modifier.fillMaxWidth(),
        )
    }
}

@Composable
fun FreeTextField(question: TextQ, value: String?, problem: String?, onChange: (String) -> Unit) {
    Column(Modifier.fillMaxWidth().padding(vertical = 8.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
        QuestionLabel(question, problem)
        OutlinedTextField(
            value = value.orEmpty(),
            onValueChange = onChange,
            isError = problem != null,
            modifier = Modifier.fillMaxWidth(),
        )
    }
}
