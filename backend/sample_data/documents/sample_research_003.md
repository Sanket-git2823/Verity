# Neural Network Architectures and Transformer Models

## Introduction

The field of deep learning has undergone a dramatic architectural shift over the past decade. Recurrent neural networks and convolutional neural networks, once the dominant paradigms for sequence modeling and feature extraction, have been increasingly displaced by **transformer architectures**. Introduced in the landmark 2017 paper "Attention Is All You Need," the transformer relies entirely on attention mechanisms to model relationships between elements of a sequence, enabling unprecedented parallelism and scalability. This document surveys the architectural evolution from early neural networks to modern transformer variants.

## Foundations: Feed-Forward and Recurrent Networks

A **feed-forward neural network** consists of layers of neurons where information flows in a single direction — from input through one or more hidden layers to an output. Each neuron computes a weighted sum of its inputs, adds a bias, and passes the result through a non-linear activation function (ReLU, sigmoid, or tanh). Feed-forward networks are universal approximators but have no mechanism for handling sequential or temporal data.

**Recurrent Neural Networks (RNNs)** address sequential data by introducing connections that loop back, allowing the hidden state at time step *t* to depend on the hidden state at step *t−1*. This recurrence gives RNNs a form of memory. However, vanilla RNNs struggle with **vanishing and exploding gradients** over long sequences. **Long Short-Term Memory (LSTM)** networks mitigate this through gating mechanisms — input, forget, and output gates — that regulate the flow of information through a persistent cell state. **Gated Recurrent Units (GRUs)** simplify the LSTM architecture by merging the cell and hidden states, using reset and update gates.

Despite their theoretical appeal, RNNs process sequences step by step, making them inherently sequential and difficult to parallelize on modern hardware.

## Convolutional Neural Networks

**Convolutional Neural Networks (CNNs)** apply learnable filters (kernels) across spatial or temporal dimensions to extract local patterns. In computer vision, hierarchical stacking of convolutional layers captures progressively more abstract features — edges, textures, object parts, and whole objects. Architectures like **ResNet** introduced skip connections that enable training of very deep networks (hundreds of layers) by providing gradient highways that bypass intermediate layers.

CNNs have also been applied to text through models like **TextCNN**, which convolve filters of varying widths across word embedding sequences to capture n-gram features. However, the fixed receptive field of convolutions limits their ability to model very long-range dependencies.

## The Transformer Architecture

The transformer eliminates recurrence and convolution entirely, relying on **self-attention** to model relationships between all positions in a sequence simultaneously.

### Self-Attention Mechanism

Given an input sequence, self-attention projects each token embedding into three vectors: **query (Q)**, **key (K)**, and **value (V)**. The attention score between positions *i* and *j* is computed as the dot product of Q_i and K_j, scaled by the square root of the key dimension to prevent gradient saturation. A softmax over all positions produces attention weights, and the output for position *i* is the weighted sum of all value vectors. This mechanism allows every token to attend directly to every other token, regardless of distance.

### Multi-Head Attention

Rather than computing a single attention function, the transformer uses **multi-head attention**: it runs *h* parallel attention heads, each with independent learned projections for Q, K, and V. The outputs of all heads are concatenated and projected through a final linear layer. This allows the model to jointly capture different types of relationships — syntactic, semantic, positional — in different subspaces.

### Positional Encoding

Since self-attention is permutation-equivariant (it has no inherent notion of order), transformers inject positional information through **positional encodings**. The original architecture uses fixed sinusoidal functions of varying frequencies, while later models like BERT and GPT use learned positional embeddings. **Rotary Position Embeddings (RoPE)**, used in LLaMA and other recent models, encode relative position directly into the attention computation.

### Encoder-Decoder and Decoder-Only Variants

The original transformer follows an **encoder-decoder** architecture: the encoder processes the input sequence with bidirectional self-attention, while the decoder generates output tokens autoregressively using masked (causal) self-attention plus cross-attention to the encoder output. **BERT** uses only the encoder for bidirectional representation learning. **GPT** and its successors use only the decoder stack with causal masking, enabling left-to-right text generation at scale.

## Scaling and Modern Variants

Modern large language models (LLMs) like GPT-4, Claude, and LLaMA scale the decoder-only transformer to billions or trillions of parameters. Architectural refinements include **pre-norm residual connections** (applying layer normalization before rather than after sub-layers), **SwiGLU activation functions**, **grouped-query attention** (reducing the KV cache memory footprint), and **flash attention** (an IO-aware algorithm that computes exact attention with reduced memory access).

## Conclusion

The transformer has become the universal backbone of modern AI, powering applications from machine translation and text generation to image recognition and protein structure prediction. Its combination of parallelism, expressivity, and scalability makes it uniquely suited to the era of large-scale pre-training and fine-tuning.
