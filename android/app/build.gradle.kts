import java.util.Properties
import java.io.FileInputStream

plugins {
    id("com.android.application")
    id("com.chaquo.python")}

// Release signing is configured through keystore.properties, which
// `pydrud keygen` writes and .gitignore excludes. Without it, release
// builds fall back to the debug key so `pydrud build --release` still works.
val keystorePropertiesFile = rootProject.file("keystore.properties")
val keystoreProperties = Properties()
val hasKeystore = keystorePropertiesFile.exists()
if (hasKeystore) {
    keystoreProperties.load(FileInputStream(keystorePropertiesFile))
}

android {
    namespace = "com.pydrud.pydash"
    compileSdk = 36
    ndkVersion = System.getenv("PYDRUD_NDK_VERSION") ?: "28.2.13676358"

    defaultConfig {
        applicationId = "com.pydrud.pydash"
        minSdk = 24
        targetSdk = 36
        versionCode = 1
        versionName = "1.0.0"

        ndk {
            abiFilters += listOf("arm64-v8a", "armeabi-v7a", "x86_64")
        }
    }

    signingConfigs {
        if (hasKeystore) {
            create("release") {
                storeFile = rootProject.file(keystoreProperties["storeFile"] as String)
                storePassword = keystoreProperties["storePassword"] as String
                keyAlias = keystoreProperties["keyAlias"] as String
                keyPassword = keystoreProperties["keyPassword"] as String
            }
        }
    }

    buildTypes {
        release {
            // R8 shrinking is opt-in: `pydrud build --release --shrink`
            // (or -PpydrudShrink=true) typically removes 30-40% of the APK.
            isMinifyEnabled = (project.findProperty("pydrudShrink") ?: "false") == "true"
            isShrinkResources = isMinifyEnabled
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro"
            )
            signingConfig = if (hasKeystore) {
                signingConfigs.getByName("release")
            } else {
                signingConfigs.getByName("debug")
            }
        }
        debug {
            isMinifyEnabled = false
        }
    }

    bundle {
        language { enableSplit = false }   // Chaquopy needs every locale
    }

    packaging {
        resources {
            excludes += setOf("META-INF/LICENSE*", "META-INF/NOTICE*",
                              "META-INF/*.kotlin_module")
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
}

// Chaquopy — embed Python in the APK.
chaquopy {
    defaultConfig {
        buildPython(System.getenv("PYDRUD_PYTHON") ?: "C:/Users/MurShidM/AppData/Local/Programs/Python/Python312/python.exe")
        version = "3.11"

        // Chaquopy can only compile source to .pyc when buildPython has the
        // same minor version as the embedded runtime. Pydrud sets this false
        // automatically on machines which only have a different Python
        // version, avoiding a scary-but-harmless Gradle warning.
        pyc {
            src = (System.getenv("PYDRUD_COMPILE_PYC") ?: "true").toBoolean()
        }

        // Managed by `pydrud pip add` — edit pydrud.toml, not this block.
        pip {
            // pydrud:pip:begin            // pydrud:pip:end
        }
    }
    sourceSets {
        getByName("main") {
            srcDir("../../src")
        }
    }
}

dependencies {
    implementation("androidx.appcompat:appcompat:1.7.0")
    implementation("androidx.core:core:1.13.1")
    implementation("androidx.swiperefreshlayout:swiperefreshlayout:1.1.0")
    implementation("androidx.recyclerview:recyclerview:1.3.2")
    implementation("androidx.security:security-crypto:1.1.0-alpha06")
    implementation("androidx.work:work-runtime:2.9.1")
    implementation("androidx.biometric:biometric:1.1.0")
    implementation("androidx.camera:camera-core:1.3.4")
    implementation("androidx.camera:camera-camera2:1.3.4")
    implementation("androidx.camera:camera-lifecycle:1.3.4")
    implementation("androidx.camera:camera-view:1.3.4")
    implementation("androidx.camera:camera-video:1.3.4")
    // Barcode/QR scanning for page.camera.scan() (bundled, works offline).
    implementation("com.google.mlkit:barcode-scanning:17.3.0")
    implementation("com.google.android.material:material:1.12.0")}

// Redirect Android assets to the project-level directory from pydrud.yaml.
android.sourceSets["main"].assets.srcDirs("../../assets")
