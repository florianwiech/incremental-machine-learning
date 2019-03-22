#!/usr/bin/python3

import tensorflow as tf
import numpy as np
import logging

from pprint import pprint

class Network():

    n_input = 784  # MNIST data input (img shape: 28*28)
    n_hidden_1 = 800  # 1st layer number of neurons
    n_hidden_2 = 800  # 2st layer number of neurons
    n_hidden_3 = 800  # 3st layer number of neurons
    n_classes = 10  # MNIST total classes (0-9 digits)

    logits = None
    loss = None
    accuracy = None

    saver = None

    def __init__(self, x, y):

        with tf.variable_scope("network"):
            self.theta = {
                'wh1':  tf.Variable(tf.truncated_normal([self.n_input, self.n_hidden_1], stddev=0.1, dtype=tf.float32), name='wh1'),
                'wh2':  tf.Variable(tf.truncated_normal([self.n_hidden_1, self.n_hidden_2], stddev=0.1, dtype=tf.float32), name='wh2'),
                'wh3':  tf.Variable(tf.truncated_normal([self.n_hidden_2, self.n_hidden_3], stddev=0.1, dtype=tf.float32), name='wh3'),
                'wo':   tf.Variable(tf.truncated_normal([self.n_hidden_3, self.n_classes], stddev=0.1, dtype=tf.float32), name='wo'),
                'bh1':  tf.Variable(tf.ones([self.n_hidden_1], dtype=tf.float32)*0.1, name='bh1'),
                'bh2':  tf.Variable(tf.ones([self.n_hidden_2], dtype=tf.float32)*0.1, name='bh2'),
                'bh3':  tf.Variable(tf.ones([self.n_hidden_3], dtype=tf.float32)*0.1, name='bh3'),
                'bo':   tf.Variable(tf.ones([self.n_classes], dtype=tf.float32)*0.1, name='bo')
            }

        with tf.variable_scope("ewc"):
            with tf.variable_scope("gradients"):
                self.gradients = {
                    'wh1':  tf.Variable(tf.zeros([self.n_input, self.n_hidden_1], dtype=tf.float32), name='wh1', trainable=False),
                    'wh2':  tf.Variable(tf.zeros([self.n_hidden_1, self.n_hidden_2], dtype=tf.float32), name='wh2', trainable=False),
                    'wh3':  tf.Variable(tf.zeros([self.n_hidden_2, self.n_hidden_3], dtype=tf.float32), name='wh3', trainable=False),
                    'wo':   tf.Variable(tf.zeros([self.n_hidden_3, self.n_classes], dtype=tf.float32), name='wo', trainable=False),
                    'bh1':  tf.Variable(tf.zeros([self.n_hidden_1], dtype=tf.float32), name='bh1', trainable=False),
                    'bh2':  tf.Variable(tf.zeros([self.n_hidden_2], dtype=tf.float32), name='bh2', trainable=False),
                    'bh3':  tf.Variable(tf.zeros([self.n_hidden_3], dtype=tf.float32), name='bh3', trainable=False),
                    'bo':   tf.Variable(tf.zeros([self.n_classes], dtype=tf.float32), name='bo', trainable=False)
                }
            with tf.variable_scope("variables"):
                self.variables = {
                    'wh1':  tf.Variable(tf.zeros([self.n_input, self.n_hidden_1], dtype=tf.float32), name='wh1', trainable=False),
                    'wh2':  tf.Variable(tf.zeros([self.n_hidden_1, self.n_hidden_2], dtype=tf.float32), name='wh2', trainable=False),
                    'wh3':  tf.Variable(tf.zeros([self.n_hidden_2, self.n_hidden_3], dtype=tf.float32), name='wh3', trainable=False),
                    'wo':   tf.Variable(tf.zeros([self.n_hidden_3, self.n_classes], dtype=tf.float32), name='wo', trainable=False),
                    'bh1':  tf.Variable(tf.zeros([self.n_hidden_1], dtype=tf.float32), name='bh1', trainable=False),
                    'bh2':  tf.Variable(tf.zeros([self.n_hidden_2], dtype=tf.float32), name='bh2', trainable=False),
                    'bh3':  tf.Variable(tf.zeros([self.n_hidden_3], dtype=tf.float32), name='bh3', trainable=False),
                    'bo':   tf.Variable(tf.zeros([self.n_classes], dtype=tf.float32), name='bo', trainable=False)
                }

        self.keys = self.theta.keys()  ;
        self.var_list = [self.theta[key] for key in self.keys] ;
        self.fisher_var_list = [self.variables[key] for key in self.keys] ;
        self.fisher_gradvar_list = [self.gradients[key] for key in self.keys] ;

        self.__neural_network__(x, y, self.theta)

    def __neural_network__(self, x, y, t: list):
        # Hidden fully connected layer with 200 neurons
        layer_1 = tf.nn.relu(tf.add(tf.matmul(tf.cast(x,tf.float32), t['wh1']), t['bh1']))

        # Hidden fully connected layer with 200 neurons
        layer_2 = tf.nn.relu(tf.add(tf.matmul(layer_1, t['wh2']), t['bh2']))

        # Hidden fully connected layer with 200 neurons
        layer_3 = tf.nn.relu(tf.add(tf.matmul(layer_2, t['wh3']), t['bh3']))

        # Output fully connected layer with a neuron for each class
        out_layer = tf.matmul(layer_3, t['wo']) + t['bo']

        # Construct model
        self.logits = out_layer

        # Define loss and optimizer V2??
        self.loss = tf.reduce_mean(tf.nn.softmax_cross_entropy_with_logits(
            logits=self.logits, labels=y))
        print("DTYPES",y,self.logits)

        self.fisherLoss = - tf.reduce_sum(tf.cast(y,tf.float32) * tf.nn.log_softmax(self.logits)) ;
        self.ewc = tf.constant(0.) ;

        # Evaluate model
        correct_pred = tf.equal(
            tf.argmax(self.logits, 1), tf.argmax(y, 1))
        self.accuracy = tf.reduce_mean(tf.cast(correct_pred, tf.float32))

        # tensorflow saver
        self.saver = tf.train.Saver(var_list = self.var_list + self.fisher_var_list + self.fisher_gradvar_list) ;

    def compute_fisher(self, sess, iterator_initializer):

        # fisher matrix opimizer
        fisher_matrix_gradients = { key: tf.square(tf.gradients(self.fisherLoss,self.theta[key])[0]) for key in self.keys} ;
        acc_np = {key: np.zeros(fisher_matrix_gradients[key].get_shape().as_list()) for key in self.keys} ;

        # log gradient tensor list
        logging.debug(fisher_matrix_gradients)

        # init iterator
        sess.run(iterator_initializer)

        iterations = 0
        try:
            while True:
                # advance iterator! Compute squared grads and download them to np
                fisher_matrix_gradients_np = sess.run(fisher_matrix_gradients)

                # accumulate them in np arrays
                for key in self.keys:
                    acc_np[key][:] += fisher_matrix_gradients_np[key]

                iterations += 1
                logging.debug(str(iterations))
        except tf.errors.OutOfRangeError:
          # when iterator is through, normalize by nr of iterations
          mx = -1 ;
          for key in self.keys:
              acc_np[key] /= (float(iterations)*1000.) ;
              _mx = acc_np[key].max() ;
              if _mx > mx:
                mx = _mx ;
          for key in self.keys:
              #acc_np[key] /= mx ;
              sess.run(tf.assign(self.gradients[key], acc_np[key])) ;
              print ("FM key=", key, acc_np[key].min(), acc_np[key].max() ) ;
          for key in self.keys:
              sess.run(tf.assign(self.variables[key], self.theta[key])) ;

    def compute_ewc(self):
        self.ewc = 0.;
        # loop over pairs of (key,fmat_tf_variable)
        for key in self.keys:
            # calc EWC appendix
            subAB = tf.subtract(
                self.theta[key], self.variables[key])
            powAB = tf.square(subAB)
            multiplyF = tf.multiply(powAB, self.gradients[key])

            self.ewc +=  tf.reduce_sum(multiplyF)

    def train(self, sess:tf.Session, update, iter_init, training_iters:int, display_steps=100, *args):
        # init iterator
        sess.run(iter_init)

        for step in range(training_iters):
            l, e, _, acc, resargs = sess.run([self.loss, self.ewc_appendix, update, self.accuracy, args])
            if step % display_steps == 0:
                logging.info(
                    "Step: {}, loss: {:.3f}, ewc:{:.3f}, training accuracy: {:.2f}".format(
                        step, l, e, acc * 100.,) + "; args: " + str(resargs[:])
                )

    def test(self, sess, iter_init):
        # init iterator
        sess.run(iter_init)

        iterations = 0
        avg_acc = 0
        try:
            while True:
                acc = sess.run([self.accuracy])
                avg_acc += acc[0]
                iterations += 1
        except tf.errors.OutOfRangeError:
            avg_acc = ((avg_acc / float(iterations)) * 100.)
            logging.info("Average validation set accuracy over {} iterations is {:.2f}%".format(iterations, avg_acc))

        return avg_acc
