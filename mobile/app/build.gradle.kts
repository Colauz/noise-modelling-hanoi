plugins {
    alias(libs.plugins.android.application)
    alias(libs.plugins.kotlin.compose)
}

/**
 * The study's own outputs, copied into the APK at build time.
 *
 * Copied, never transcribed. The repository's rule is that no published number is
 * ever written out by hand — `models/metrics.json` is the single source of truth
 * and `10_build_report.py` refuses to run without it. An app that displays the
 * headline R2 is bound by the same rule, so it reads the same file. Re-run the
 * pipeline, rebuild the APK, and the app moves with it; there is no second place
 * for a number to go stale.
 *
 * A typed task rather than a bare `Copy`, because AGP 9 wires generated sources
 * through the variant API and that needs an output `DirectoryProperty`, which
 * `Copy` does not expose.
 */
abstract class SyncStudyData : DefaultTask() {

    @get:InputFiles
    @get:PathSensitive(PathSensitivity.RELATIVE)
    abstract val dataFiles: ConfigurableFileCollection

    @get:InputFiles
    @get:PathSensitive(PathSensitivity.RELATIVE)
    abstract val figures: ConfigurableFileCollection

    @get:OutputDirectory
    abstract val outputDirectory: DirectoryProperty

    @get:Inject
    abstract val fs: FileSystemOperations

    @TaskAction
    fun sync() {
        val out = outputDirectory.get().asFile
        fs.delete { delete(out) }
        fs.copy {
            from(dataFiles)
            into(out)
        }
        fs.copy {
            from(figures)
            into(File(out, "figures"))
        }
    }
}

val repoRoot: File = rootDir.parentFile

val syncStudyData by tasks.registering(SyncStudyData::class) {
    description = "Copies the published datasets, model and figures into the app's assets."
    dataFiles.from(
        File(repoRoot, "results/maps/hanoi_noise_map.csv"),
        File(repoRoot, "data/processed/measurements.csv"),
        File(repoRoot, "models/metrics.json"),
        File(repoRoot, "models/hybrid_physical.json"),
    )
    figures.from(
        fileTree(File(repoRoot, "results/figures")) {
            include("analyse_*.png", "validation_simulation.png")
        }
    )
}

android {
    namespace = "org.noisehanoi.mobile"
    compileSdk = 36

    defaultConfig {
        applicationId = "org.noisehanoi.mobile"
        // 26: AudioRecord + runtime permissions behave consistently from Oreo on,
        // and the field phones in the Hanoi campaign were all above it.
        minSdk = 26
        targetSdk = 36
        versionCode = 1
        versionName = "0.1.0"
    }

    /**
     * The Kobo account a built APK submits to, supplied at build time and absent
     * from the source.
     *
     * In anonymous mode the account name is the only thing routing a submission
     * to a project, so a publicly distributed APK has to carry one — users will
     * not type it. Hard-coding it would put one person's account into every
     * installed copy, make the campaign personally theirs, and require a new
     * release to move. A build property leaves the repository with no account
     * name in it and makes choosing one — ideally an institutional account, not
     * an individual's — a deliberate act by whoever builds the public APK:
     *
     *     ./gradlew assembleRelease -Pnoisehanoi.koboUser=the-account
     *
     * Empty is the default, and an empty value means the app asks in Settings.
     */
    defaultConfig {
        buildConfigField(
            "String",
            "DEFAULT_KOBO_USER",
            "\"" + (providers.gradleProperty("noisehanoi.koboUser").orNull ?: "") + "\"",
        )
    }

    buildTypes {
        release {
            isMinifyEnabled = false
            proguardFiles(getDefaultProguardFile("proguard-android-optimize.txt"), "proguard-rules.pro")
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    kotlin {
        compilerOptions {
            jvmTarget.set(org.jetbrains.kotlin.gradle.dsl.JvmTarget.JVM_17)
        }
    }

    buildFeatures {
        compose = true
        buildConfig = true   // BuildConfig.VERSION_NAME goes into the submission metadata
    }
}

androidComponents {
    onVariants { variant ->
        variant.sources.assets?.addGeneratedSourceDirectory(syncStudyData, SyncStudyData::outputDirectory)
    }
}

dependencies {
    implementation(libs.androidx.core.ktx)
    implementation(libs.androidx.lifecycle.runtime.ktx)
    implementation(libs.androidx.activity.compose)

    implementation(platform(libs.androidx.compose.bom))
    implementation(libs.androidx.ui)
    implementation(libs.androidx.ui.graphics)
    implementation(libs.androidx.ui.tooling.preview)
    implementation(libs.androidx.material3)
    implementation(libs.androidx.navigation.compose)
    implementation(libs.androidx.lifecycle.viewmodel.compose)
    implementation(libs.androidx.work.runtime.ktx)
    implementation(libs.okhttp)

    testImplementation(libs.junit)

    debugImplementation(libs.androidx.ui.tooling)
}
