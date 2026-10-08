# Pydrud R8 / ProGuard configuration.
#
# Shrinking is off by default; enable it with:
#     pydrud build --release --shrink
# Typical savings are 30-40% of the Java/Kotlin portion of the APK. The
# Python runtime and your .py sources are assets, so they are untouched —
# use `pydrud build --release --abi arm64-v8a` to halve *that* half.

# ── Chaquopy / Python runtime ────────────────────────────────────────────
-keep class com.chaquo.python.** { *; }
-keep class org.jetbrains.annotations.** { *; }
-dontwarn com.chaquo.python.**

# ── Pydrud runtime backend ───────────────────────────────────────────────
# PydrudRuntimeFactory constructs the active backend by name, so R8 must not
# strip it or the interface it implements.
-keep class com.pydrud.pydash.PydrudRuntimeFactory { *; }
-keep class com.pydrud.pydash.PythonRuntime { *; }
-keep class com.pydrud.pydash.ChaquopyRuntime { *; }

# Python calls into these by name through reflection, so they must keep
# their exact names even when everything else is renamed.
-keep class com.pydrud.pydash.PydashActivity { *; }
-keep class com.pydrud.pydash.BridgeService { *; }
-keep class com.pydrud.pydash.ViewFactory { *; }
-keep class com.pydrud.pydash.MaterialViews { *; }
-keep class com.pydrud.pydash.AdvancedViews { *; }
-keep class com.pydrud.pydash.NativeServices { *; }
-keep class com.pydrud.pydash.PlatformServices { *; }
-keep class com.pydrud.pydash.GestureBinder { *; }
-keep class com.pydrud.pydash.EventDispatcher { *; }
-keep class com.pydrud.pydash.PydrudWorker { *; }
-keep class com.pydrud.pydash.WidgetRegistry { *; }

# ── AndroidX pieces reached reflectively ─────────────────────────────────
-keep class androidx.work.** { *; }
-keep class androidx.camera.** { *; }
-keep class androidx.security.crypto.** { *; }
-keep class androidx.biometric.** { *; }
-keepclassmembers class * extends androidx.work.Worker {
    public <init>(android.content.Context, androidx.work.WorkerParameters);
}

# Views inflated from XML / by name.
-keepclassmembers class * extends android.view.View {
    public <init>(android.content.Context);
    public <init>(android.content.Context, android.util.AttributeSet);
    public void set*(***);
    *** get*();
}

# Keep annotations and signatures so reflection and stack traces survive.
-keepattributes *Annotation*, Signature, InnerClasses, EnclosingMethod
-keepattributes SourceFile, LineNumberTable
-renamesourcefileattribute SourceFile

# ── Optional integrations ────────────────────────────────────────────────
-dontwarn com.google.firebase.**
-keep class com.google.firebase.** { *; }
-dontwarn org.osmdroid.**
