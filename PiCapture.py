#!/usr/bin/python
import os
import sys
import time
import glob
import shutil
import argparse
import datetime
import threading
import subprocess

logOnConsole = False
def log(str):
	global logOnConsole
	if logOnConsole:
		print str	

def initializeDir(dirname):
	if not os.path.isdir(dirname):
		os.makedirs(dirname)
		log('Created directory: {0}'.format(dirname))

def renameCapturedFiles(dirname, filePrefix, fileExtension):
	capturedFiles = glob.glob('{0}/{1}*{2}'.format(dirname, filePrefix, fileExtension))
	for file in capturedFiles:
		newFilename = datetime.datetime.fromtimestamp(os.path.getctime(file)).strftime(
			'{0}/%H%M%S{1}'.format(dirname, os.path.splitext(file)[1]))
		os.rename(file, newFilename)
		log('renamed {0} -> {1}'.format(file, newFilename))

def cmpImages(img1, img2):
	if not os.path.isfile(img1):
		return False
	if not os.path.isfile(img2):
		return False
	# first check if the two images are different in size by a threshold
	sz1 = os.stat(img1).st_size
	sz2 = os.stat(img2).st_size
	s1 = max(sz1,sz2)
	s2 = max(1, min(sz1,sz2))
	perc = ((s1/s2) - 1) * 100
	if perc > 20:
		return False
	# next check the result of perceptual diff
	try:
		args = ['perceptualdiff', '-downsample', '3', '-colorfactor', '0', img1, img2]
		subprocess.check_output(args, shell=False)
		return True
	except subprocess.CalledProcessError:
		return False
	except OSError:
		print 'Error running perceptualdiff'
		return False

def freeDiskSpace(dir):
	for i in range(10):	# retry few times
		st = os.statvfs('/')
		bavail = st.f_frsize * st.f_bavail # available disk space in bytes
		if bavail < (1024*1024*512): # if available disk space is less than a threshold, free some more
			canDelete = [os.path.join(dir, o) for o in sorted(os.listdir(dir)) if os.path.isdir(os.path.join(dir, o))]
			if len(canDelete) <= 1:
				break
			log('freeing disk-space by deleting: {0}'.format(canDelete[0]))
			shutil.rmtree(canDelete[0])
		else:
			break		

def killProc(proc):
	if proc:
		proc.terminate()

runBGThread=False
def bgThread(timeLapse, dir, imgPrefix, imgExt):
	global runBGThread
	while runBGThread:
		try:
			renameCapturedFiles(dir, imgPrefix, imgExt)
			# process (erase similar images) recently captured images (.jpeg)
			images = sorted(glob.glob('{0}/*{1}'.format(dir, imgExt)))
			cImages = len(images)
			if cImages <= 1:
			 	time.sleep(timeLapse*4)
				# if no more images were captured even after sleeping, exit this thread
				if len(sorted(glob.glob('{0}/*{1}'.format(dir, imgExt)))) == cImages:
					return
				continue
			prevImg = None
			for img in images:
				if not runBGThread:
					renameCapturedFiles(dir, imgPrefix, imgExt)
					return
				if prevImg: 
					if cmpImages(prevImg, img):
						# img is similar to prevImg, delete prevImg
						os.remove(prevImg)
						log('deleting dup: {0}'.format(prevImg))
					else:
						# prevImg is different than img, keep it and
						# rename to .jpg so we dont process it again in next outer loop cycle
						os.rename(prevImg, '{0}.jpg'.format(os.path.splitext(prevImg)[0]))
				prevImg = img
		except Exception, ex:
			print "Exception in bgThread: {0} - {1}".format(type(ex).__name__, ex)

noirOptimization = '-ex night -drc high'
def captureImages(storageRoot, timeLapse=15):
	global runBGThread
	bgThreadDir = None
	filePrefix = 'img'
	fileExt = '.jpeg'
	while True:
		try:
			freeDiskSpace(storageRoot) # free disk space before starting capture
			dt = datetime.datetime.now()
			runDuration = 86400 - (dt.hour*3600 + dt.minute*60 + dt.second)
			# capture atleast 1 shot in a run
			if timeLapse > runDuration:
				timeLapse = runDuration				
			# start a run
			currentDirname = '{0}/{1}'.format(storageRoot, dt.date().strftime('%Y%m%d'))
			initializeDir(currentDirname)
			cmdline = 'raspistill -w 1280 -h 960 --thumb none --exif none -n -q 50 -tl {0} -t {1} -o {2}'.format(
				timeLapse*1000, runDuration*1000, '{0}/{1}%05d{2}'.format(currentDirname, filePrefix, fileExt))
			proc = subprocess.Popen(cmdline.split() + noirOptimization.split(), shell=False)
			log('Capturing images (pid={0}) to {1}'.format(proc.pid, currentDirname))
			if currentDirname != bgThreadDir:
				# if we are capturing in a different directory than bgThreadDir, start a new thread
				# this thread will auto-exit when there are no new images being captured for currentDirname
				runBGThread = True
				bgThreadDir = currentDirname
				threading.Thread(target=bgThread, args=[timeLapse, bgThreadDir, filePrefix, fileExt]).start()
			time.sleep(runDuration)
			killProc(proc)
		except KeyboardInterrupt:
			killProc(proc)
			runBGThread = False	# signal all bgthreads to exit
			print 'waiting for background worker threads to exit'
 			return

def captureVideo(storageRoot, captureSpeed, videoStabilization):
	filePrefix = 'vid'	
	fileExt = '.h264'
	while True:
		try:
			freeDiskSpace(storageRoot) # free disk space before starting capture
			dt = datetime.datetime.now()
			runDuration = 86400 - (dt.hour*3600 + dt.minute*60 + dt.second)
			# start a run
			currentDirname = '{0}/{1}'.format(storageRoot, dt.date().strftime('%Y%m%d'))
			initializeDir(currentDirname)
			filename = '{0}/{1}00{2}'.format(currentDirname, filePrefix, fileExt)
			cmdline = 'raspivid -w 800 -h 600 -qp 25 -fps {0} -t {1} -o {2}'.format(
				30/captureSpeed, runDuration*1000, filename)
			if videoStabilization:
				cmdline += ' -vs'
			proc = subprocess.Popen(cmdline.split() + noirOptimization.split(), shell=False)
			log('Capturing video (pid={0}) to {1} @ {2}x'.format(proc.pid, filename, captureSpeed))
			time.sleep(runDuration)
			killProc(proc)
			renameCapturedFiles(currentDirname, filePrefix, fileExt)
		except KeyboardInterrupt:
			killProc(proc)
			renameCapturedFiles(currentDirname, filePrefix, fileExt)
 			return

if __name__ == '__main__':
	parser = argparse.ArgumentParser(
		description='RapberryPi timelapse/video capture helper. Requires perceptualdiff which is used to cleanup duplicate captures in a timelapse.'
	)
	parser.add_argument('-d',  metavar='directory', default='./cam', help='Directory where captured files are stored. Default: ./cam')
	parser.add_argument('-l', action='store_true', default=False, help='Log information on console')
	parser.add_argument('-t', metavar='seconds', type=int, help='Start timelapse capture with given duration in seconds')
	parser.add_argument('-v', action='store_true', help='Start video capture')
	parser.add_argument('-vf', metavar='speed_factor', default=2, type=int, help='Changes captured video speed by given factor. Default: 2')
	parser.add_argument('-vs', action='store_true', default=False, help='Turn on video stabilization')
	args = parser.parse_args()
	logOnConsole = args.l
	storageRoot = args.d	
	if args.v:
		captureVideo(storageRoot, args.vf, args.vs)
	elif args.t:
		captureImages(storageRoot, args.t)
	else:
		parser.print_help()
