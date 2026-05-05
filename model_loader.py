import os
import tensorflow as tf

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

efficient_path = os.path.join(BASE_DIR, "models", "efficientnet_final.h5")
custom_path = os.path.join(BASE_DIR, "models", "custom_cnn_finetuned.h5")

efficientnet_model = tf.keras.models.load_model(efficient_path)
custom_model = tf.keras.models.load_model(custom_path)


def get_model(name):
    name = name.lower().strip()   # 🔥 important

    if name in ["efficient", "efficientnet"]:
        return efficientnet_model

    elif name in ["custom", "custom_cnn"]:
        return custom_model

    else:
        raise ValueError(f"Invalid model selected: {name}")