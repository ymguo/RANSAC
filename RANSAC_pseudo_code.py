#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Aug 30 09:44:25 2019

@author: ymguo
"""
'''
#code2:
【Reading】
# We haven't told RANSAC algorithm this week. So please try to do the reading.
# And now, we can describe it here:

We have 2 sets of points, say, Points A and Points B. 
We use A.1 to denote the first point in A, B.2 the 2nd point in B and so forth.
Ideally, A.1 is corresponding to B.1, ... A.m corresponding B.m. 
However, it's obvious that the matching cannot be so perfect and the matching in our real world is like: 
A.1-B.13, A.2-B.24, A.3-x (has no matching), x-B.5, A.4-B.24(This is a wrong matching) ...
# The target of RANSAC is to find out the true matching within this messy.
  
# Algorithm for this procedure can be described like this:

# 1. Choose 4 pair of points randomly in our matching points. 
Those four called "inlier" (中文： 内点) while others "outlier" (中文： 外点)
# 2. Get the homography of the inliers
# 3. Use this computed homography to test all the other outliers. 
And separated them by using a threshold into two parts:
#  a. new inliers which is satisfied our computed homography
#  b. new outliers which is not satisfied by our computed homography.
# 4. Get our all inliers (new inliers + old inliers) and goto step 2
# 5. As long as there's no changes or we have already repeated step 2-4 k, 
a number actually can be computed,times, we jump out of the recursion. 
The final homography matrix will be the one that we want.

# [WARNING!!! RANSAC is a general method. Here we add our matching background to that.]

# Your task: please complete pseudo code (it would be great if you hand in real code!) of this procedure.

#       Python:
#       def ransacMatching(A, B):
#           A & B: List of List
#

'''
# use RANSAC to find keypoint matches
# Using RANSAC Algorithm to Estimate the Homography Matrix 
# of Perspective Transformation透视变换.

import os
import cv2
import numpy as np
import torch
from torch.autograd import Variable
import random

#matplotlib inline
from matplotlib import pylab as plt

def get_normalized(P1, P2):
    if isinstance(P1, list):
        P1 = torch.FloatTensor(P1)
    if isinstance(P2, list):
        P2 = torch.FloatTensor(P2)
    # 1.中心化
    p1_c, p2_c = P1.mean(dim=0), P2.mean(dim=0)
    print('p1_c:', p1_c)
    print('p2_c:', p2_c)
    P1 -= p1_c
    P2 -= p2_c
    # 2.归一化
    # D1, D2 = [], []
    # for p1, p2 in zip(P1, P2):
    #     D1.append(get_distance(p1, p1_c))
    #     D2.append(get_distance(p2, p2_c))
    # d1 = max(D1)  # -> tensor
    # d2 = max(D2)
    # P1 /= d1
    # P2 /= d2
    return P1, P2

def get_distance(p1, p2):
    if isinstance(p1, list):
        p1 = torch.FloatTensor(p1)
    if isinstance(p2, list):
        p2 = torch.FloatTensor(p2)
    d = torch.sqrt((p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2)
    return d

def get_perspective(p, H):
    x, y = p
    src = torch.FloatTensor([x, y, 1]).reshape(3, 1)
    u, v, w = torch.mm(H, src)
    dst = torch.FloatTensor([u/w, v/w])
    return dst

def get_init_H(src, dst):
    a = []
    b = []
    for p1, p2 in zip(src, dst):
        x, y = p1
        u, v = p2    
        ai = torch.zeros(2, 8)
        ai[0, 0:3] = torch.FloatTensor([x, y, 1.])
        ai[1, 3:6] = torch.FloatTensor([x, y, 1.])
        ai[:, 6:8] = torch.FloatTensor([[-u*x, -u*y],
                                        [-v*x, -v*y]])
        bi = torch.FloatTensor([u, v]).reshape(2,1)
        if len(a) == 0:
            a = ai
            b = bi
        else:
            a = torch.cat((a, ai), 0)
            b = torch.cat((b, bi), 0)
    H = np.linalg.solve(a, b)
    H = torch.FloatTensor(np.append(H, 1).reshape(3, 3))
    return H

def random_warp(img):
    height, width, channels = img.shape
    random_margin = 60
    # src
    x1, y1 = random.randint(-random_margin, random_margin), random.randint(-random_margin, random_margin)
    x2, y2 = random.randint(width - random_margin - 1, width - 1), random.randint(-random_margin, random_margin)
    x3, y3 = random.randint(width - random_margin - 1, width - 1), random.randint(height - random_margin - 1, height - 1)
    x4, y4 = random.randint(-random_margin, random_margin), random.randint(height - random_margin - 1, height - 1)   
    # dst
    dx1 = random.randint(-random_margin, random_margin)
    dy1 = random.randint(-random_margin, random_margin)
    dx2 = random.randint(width - random_margin - 1, width - 1)
    dy2 = random.randint(-random_margin, random_margin)
    dx3 = random.randint(width - random_margin - 1, width - 1)
    dy3 = random.randint(height - random_margin - 1, height - 1)
    dx4 = random.randint(-random_margin, random_margin)
    dy4 = random.randint(height - random_margin - 1, height - 1)    
    # warp:
    pts1 = np.float32([[x1, y1], [x2, y2], [x3, y3], [x4, y4]])
    pts2 = np.float32([[dx1, dy1], [dx2, dy2], [dx3, dy3], [dx4, dy4]])
    M_warp = cv2.getPerspectiveTransform(src=pts1, dst=pts2)
    img_warp = cv2.warpPerspective(src=img, M=M_warp, dsize=(width, height))
    return M_warp, img_warp

def ransacMatching(A, B):
    """
    Find the best Perspective Transformation Homography Matrix 'H' using RANSAC Algorithm.
    In RANSAC iterations, each time we recompute least-squares 'H' estimate using all of the inliers.

    # Follow up 1: For step 3, How to do the "test"?
        * Set a threshold 'D2', if the distance between point B.i and the one computed by 'H.dot(A.i)'
          is smaller than 'D2', then (A.i, B.i) will be added to 'new_inliers';
    
    # Follow up 2: How to decide the "k" mentioned in step 5. Think about it mathematically!
        * Set:
            s = 4  # minimum number of data points required to estimate model parameters;
            p = 0.95: probability having at least picked one set of inliers after iterations;
            e = 0.5: probability that a point is an inlier;
          then the maximum number of iterations 'K' allowed in the algorithm equals to 72 according to:
            1 - p = (1 - e ** s) ** K,
            then K = log(1-p) / log(1 - e ** s).
    -----------------------------------------------------------------------------
    Parameters:
        A & B: list of list.
    """
    assert len(A) == len(B)
    p = 0.95  # probability having at least picked one set of inliers after iterations 
    S = 4  # minimum number of data points required to estimate model parameters
    E = 0.5  # probability that a point is an inlier
    K = 72  # maximum number of iterations allowed in the algorithm
    MAX_ITERS = 1000  # maximum number of iterations allowed in the algorithm
    N = len(A)
    sigma = torch.FloatTensor([get_distance(p1, p2) for p1, p2 in zip(A, B)]).std()
    T = np.sqrt(5.99) * sigma
    dtype = torch.FloatTensor  # torch.float32
    LR = 1e-2
    MOMENTUM = 0.9
    
    # (0) Normalization：---------------------------------------------------------------------------------------------------------------  
    # A, B = get_normalized(A, B)  # torch.FloatTensor
    A = torch.FloatTensor(A)
    B = torch.FloatTensor(B)
    
    # (1) Choose 'S' pair of points randomly in matching points:
    inliers = np.random.choice(range(N), size=S, replace=False).tolist()
    src = [A[_] for _ in inliers]
    dst = [B[_] for _ in inliers]
    
    # (2) Initialize the homography 'H' & loss:
    H = Variable(get_init_H(src, dst), requires_grad=True)
    optimizer = torch.optim.SGD([{'params': H},],
                                lr=LR, momentum=MOMENTUM)
    print(H)
    """ RANSAC Iterations: """
    for i in range(MAX_ITERS):
        optimizer.zero_grad()
        loss = H.sum() * 0
        H_invs = H.inverse()  # TODO: Singular matrix?
        for p1, p2 in zip(src, dst):
            f2 = get_perspective(p1, H)
            f1 = get_perspective(p2, H_invs)
            loss += (get_distance(p2, f2) + get_distance(p1, f1))
        
        # (3) Use this computed homography to test all the other outliers and separated them by using a threshold into two parts:
        new_inliers = []
        outliers =  [_ for _ in range(N) if _ not in inliers]
        for _ in outliers:
            p1 = A[_]
            p2 = B[_]
            f2 = get_perspective(p1, H)
            f1 = get_perspective(p2, H_invs)
            d1 = get_distance(p1, f1)
            d2 = get_distance(p2, f2)
            if d2 <= T and d1 <= T:
                new_inliers.append(_)
                loss += (d1 + d2)
                
        if len(new_inliers) > 0:
            # (4) Get all inliers (new inliers + old inliers) and goto step (2)
            inliers += new_inliers
            src += [A[_] for _ in new_inliers]
            dst += [B[_] for _ in new_inliers]
        else:
            # (5) If there's no changes or we have already repeated step (2)-(4) K times, jump out of the recursion.
            # The final homography matrix 'H' will be the wanted one.
            break
        loss.backward()
        optimizer.step()
    return H.detach().numpy()

'''
test
'''
img = plt.imread("IMG_6896.jpg")
plt.imshow(img)
plt.show()

h, w, c = img.shape
print(h, w)

cv2_img = cv2.imread("IMG_6896.jpg")
H, cv2_img_warp = random_warp(cv2_img)
#print(H)
img_warp = cv2.cvtColor(cv2_img_warp, cv2.COLOR_BGR2RGB)
plt.imshow(img_warp)
plt.show()

A = []
B = []
for i in range(15):
    x = random.randint(0, w-1) * 1.
    y = random.randint(0, h-1) * 1.
    A.append([x, y])
    src = np.array([x, y, 1]).reshape(3,)
    u, v, t = H.dot(src)
    B.append([u/t, v/t])

plt.figure(figsize=(10, 10))
plt.subplot(121)
plt.title("original")
for p in A:
    x, y = p
    plt.scatter(x, y, c='r')
plt.imshow(img)

plt.subplot(122)
for p in B:
    u, v = p
    plt.scatter(u, v, c='g')
plt.title("perspective transform")
plt.imshow(img_warp)
plt.show()

'''
对比H_hat和H
'''
H_hat = ransacMatching(A, B)
print('Estimated H: ', H_hat)
print('\n','H: ', H)

B_hat = []
for p in A:
    x, y = p
    src = np.array([x, y, 1]).reshape(3, 1)
    u, v, t = H_hat.dot(src).ravel()
    B_hat.append([u/t, v/t])
    
'''
对比B_hat和B
'''    
print('\n','B_hat:', B_hat)
print('\n','B:', B)

save_path = "./result_RANSAC"
if not os.path.exists(save_path):
    os.mkdir(save_path)

plt.figure(figsize=(15, 15))

plt.subplot(131)
plt.title("original")
for p in A:
    x, y = p
    plt.scatter(x, y, c='r')
plt.imshow(img)

plt.subplot(132)
for p in B:
    u, v = p
    plt.scatter(u, v, c='g')
plt.title("perspective transform")  # B (H)
plt.imshow(img_warp)

plt.subplot(133)
for p in B_hat:
    u, v = p
    plt.scatter(u, v, c='b')
plt.title("estimated perspective transform")  # B_hat (H_hat)
plt.imshow(img_warp)
plt.savefig(save_path+"/ransac_example.jpg", dpi=1000)
plt.show()


























