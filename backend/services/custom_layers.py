import tensorflow as tf
from tensorflow import keras
from keras import layers


class SelfAttention(layers.Layer):
    """
    Self-Attention layer for sequence models
    Uses Keras's built-in Attention layer
    """
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.att = layers.Attention()

    def call(self, inputs):
        # inputs: (batch, time, features)
        # self-attention: query=key=value=inputs
        context = self.att([inputs, inputs])
        return context
    
    def get_config(self):
        config = super().get_config()
        return config
