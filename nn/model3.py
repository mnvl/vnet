
import numpy as np
import logging
import unittest
import gflags
import tensorflow as tf

class CNN3:
  def __init__(self, settings = {}):
    self.D = settings.get("D", 16)
    self.H = settings.get("H", 256)
    self.W = settings.get("W", 256)
    self.C = settings.get("C", 1)
    self.DHW = self.D * self.H * self.W

    self.minibatch_size = settings.get("minibatch_size", 10)
    self.num_classes = settings.get("num_classes", 2)

    self.conv_layers = settings.get("conv_layers", (100, 100, 100))
    self.fc_layers = settings.get("fc_layers", (50, 50))

    self.learning_rate = settings.get("learning_rate", 1e-4)
    self.l2_reg = settings.get("l2_reg", 1e-6)
    self.dropout = settings.get("dropout", 0.9)

    self.session = tf.Session()

    self.X_placeholder = tf.placeholder(tf.float32, shape=(self.minibatch_size, self.D, self.H, self.W, self.C))
    self.y_placeholder = tf.placeholder(tf.uint8, shape=(self.minibatch_size, self.D, self.H, self.W, self.num_classes))
    self.dropout_placeholder = tf.placeholder(tf.float32)
    logging.info("X_placeholder: %s" % str(self.X_placeholder.shape))
    logging.info("y_placeholder: %s" % str(self.y_placeholder.shape))

    layer_channels = [self.C] + list(self.conv_layers) + list(self.fc_layers) + [self.num_classes]
    layer_strides = [3] + [3 for x in self.conv_layers] + [1 for x in self.fc_layers] + [1]
    channels_config = list(zip(layer_channels, layer_strides))

    self.loss = tf.constant(0., tf.float32)
    Z = self.X_placeholder

    for i in range(1, len(channels_config)):
      (prev_channels, prev_stride) = channels_config[i - 1]
      (channels, stride) = channels_config[i]

      W = tf.Variable(tf.truncated_normal((stride, stride, stride, prev_channels, channels), stddev = 0.1))
      b = tf.Variable(tf.constant(0.1, shape = (channels,)))
      H = tf.nn.conv3d(Z, W, (1, 1, 1, 1, 1), "SAME") + b

      if i != len(channels_config) - 1:
        H = tf.nn.relu(H)
        Z = tf.nn.dropout(H, self.dropout_placeholder)
      else:
        Z = H

      logging.info("conv: %s" % str(Z))

      self.loss += 2. * self.l2_reg * tf.reduce_sum(W)

    conv_last_flat = tf.reshape(Z, (self.minibatch_size * self.DHW, self.num_classes))
    logging.info("conv_last_flat = %s" % str(conv_last_flat.shape))

    y_flat = tf.reshape(self.y_placeholder, (self.minibatch_size * self.DHW, self.num_classes))
    logging.info("y_flat = %s" % str(y_flat.shape))

    cross_entropy = tf.reduce_mean(
      tf.nn.softmax_cross_entropy_with_logits(labels = y_flat, logits = conv_last_flat))

    self.loss = cross_entropy

    self.debug = self.loss

    self.train_step = tf.train.AdamOptimizer(self.learning_rate).minimize(self.loss)
    self.correct_prediction = tf.equal(tf.argmax(conv_last_flat, 1), tf.argmax(y_flat, 1))
    self.accuracy = tf.reduce_mean(tf.cast(self.correct_prediction, tf.float32))

    self.session.run(tf.global_variables_initializer())

  def make_feed_dict(self, X, y):
    return {
      self.X_placeholder: X,
      self.y_placeholder: y,
      self.dropout_placeholder: self.dropout
    }

  def fit(self, X, y):
    with self.session.as_default():
      feed_dict = self.make_feed_dict(X, y)
      #print(self.debug.eval(feed_dict))
      self.train_step.run(feed_dict)
      #print(self.debug.eval(feed_dict))
      loss = self.loss.eval(feed_dict)
      accuracy = self.accuracy.eval(feed_dict)
      return (loss, accuracy)

  def evaluate(self, X, y):
    with self.session.as_default():
      return self.accuracy.eval(make_feed_dict(X, y))

class TestCNN3(unittest.TestCase):
  def make_Xy(self, H, C, override_y = None):
    X = np.random.rand(1, 16, H, H, 1)

    N = 16*H*H
    y = np.zeros(shape = (N, C), dtype = np.uint8)
    y[np.arange(N), override_y if override_y is not None else np.random.randint(0, C, N)] = 1
    y = y.reshape(1, 16, H, H, C)

    return (X, y)

  def test_overfit(self):
    H = 32
    cnn = CNN3(
      {"num_classes": 10,
       "minibatch_size": 1,
       "D": 16, "H": H, "W": H,
       "reg": 0., "dropout": 1.})
    X, y = self.make_Xy(H, 10)
    for i in range(100):
      loss, accuracy = cnn.fit(X, y)
      if i % 20 == 0: logging.info("step %d: loss = %f, accuracy = %f" % (i, loss, accuracy))

  def test_minibatch_leak(self):
    H = 32
    cnn = CNN3({"num_classes": 2, "minibatch_size": 2, "H": H, "W": H, "reg": 0})
    X1, y1 = self.make_Xy(H, 2, 0)
    X2, y2 = self.make_Xy(H, 2, 1)

    X1 *= 0.5
    X2 *= 1.5

    X = np.concatenate((X1, X2))
    y = np.concatenate((y1, y2))

    for i in range(100):
      loss, accuracy = cnn.fit(X, y)
      if i % 20 == 0: logging.info("step %d: loss = %f, accuracy = %f" % (i, loss, accuracy))

  def test_run(self):
    H = 128
    cnn = CNN3({"num_classes": 10, "minibatch_size": 1, "H": H, "W": H})
    X, y = self.make_Xy(H, 10)
    for i in range(100):
      loss, accuracy = cnn.fit(X, y)
      logging.info("loss = %f, accuracy = %f" % (loss, accuracy))


if __name__ == '__main__':
  logging.basicConfig(level=logging.DEBUG,
                      format='%(asctime)s %(levelname)s %(message)s',
                      filename='/dev/stderr',
                      filemode='w')
  unittest.main()














