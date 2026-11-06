package spirespeed;

import com.badlogic.gdx.Gdx;
import com.badlogic.gdx.backends.lwjgl.LwjglApplication;
import com.badlogic.gdx.backends.lwjgl.LwjglApplicationConfiguration;
import com.badlogic.gdx.backends.lwjgl.LwjglGraphics;
import com.evacipated.cardcrawl.modthespire.lib.SpirePatch;
import com.megacrit.cardcrawl.core.CardCrawlGame;
import java.lang.reflect.Field;

/**
 * Training speed: every frame counts as spire.frame seconds of game time, and frames are no
 * longer held to the display's rate. A longer step than about 0.1 s stalls the game's fades,
 * whose smoothing overshoots, so speed comes from more frames, not from longer ones.
 */
public class SpeedPatch {
    private static final float FRAME = Float.parseFloat(System.getProperty("spire.frame", "0"));
    private static final int FPS = Integer.parseInt(System.getProperty("spire.fps", "0"));

    @SpirePatch(clz = LwjglGraphics.class, method = "getDeltaTime")
    public static class Delta {
        public static float Postfix(float __result) {
            return FRAME > 0 ? FRAME : __result;
        }
    }

    @SpirePatch(clz = LwjglGraphics.class, method = "getRawDeltaTime")
    public static class RawDelta {
        public static float Postfix(float __result) {
            return FRAME > 0 ? FRAME : __result;
        }
    }

    @SpirePatch(clz = CardCrawlGame.class, method = "create")
    public static class Unlock {
        public static void Postfix(CardCrawlGame __instance) throws Exception {
            if (FPS == 0) {
                return;
            }
            // setVSync reports any GL error left over from loading, so clear those first.
            while (Gdx.gl.glGetError() != 0) {
                continue;
            }
            Gdx.graphics.setVSync(false);
            Field graphics = LwjglApplication.class.getDeclaredField("graphics");
            graphics.setAccessible(true);
            Field config = LwjglGraphics.class.getDeclaredField("config");
            config.setAccessible(true);
            LwjglApplicationConfiguration settings =
                (LwjglApplicationConfiguration) config.get(graphics.get(Gdx.app));
            settings.foregroundFPS = FPS;
            settings.backgroundFPS = FPS;
        }
    }
}
