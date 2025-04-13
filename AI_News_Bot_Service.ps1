# AI_News_Bot_Service.ps1

$ServiceName = "AI_News_Bot_Service"
$ExecutablePath = "D:\GitHub\ai-news-bot\main.py"
$PythonPath = "C:\Users\User\AppData\Local\Programs\Python\Python39\python.exe"
$WorkingDirectory = "D:\GitHub\ai-news-bot"
$NssmPath = "C:\Tools\nssm\nssm.exe"  # Changed path to a more likely location
$RequiredPackages = @("discord.py")  # Add more packages as needed

# Check if NSSM is installed
if (!(Test-Path $NssmPath)) {
    Write-Host "NSSM not found at $NssmPath." -ForegroundColor Yellow
    Write-Host "Searching for NSSM in common locations..." -ForegroundColor Yellow
    
    $possibleLocations = @(
        "C:\Tools\nssm\nssm.exe",
        "C:\Program Files\nssm\nssm.exe",
        "C:\Program Files (x86)\nssm\nssm.exe",
        "C:\Windows\System32\nssm.exe"
    )
    
    foreach ($location in $possibleLocations) {
        if (Test-Path $location) {
            Write-Host "Found NSSM at $location" -ForegroundColor Green
            $NssmPath = $location
            break
        }
    }
    
    if (!(Test-Path $NssmPath)) {
        Write-Host "NSSM not found. Please download it from https://nssm.cc/download" -ForegroundColor Yellow
        Write-Host "After downloading, place nssm.exe in a directory and update the `$NssmPath variable." -ForegroundColor Yellow
        exit 1
    }
}

# Check if service exists and delete it if it does
$ServiceExists = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
if ($ServiceExists) {
    Write-Host "Service already exists. Stopping and removing it..."
    Stop-Service -Name $ServiceName -Force -ErrorAction SilentlyContinue
    & $NssmPath remove $ServiceName confirm
    Start-Sleep -Seconds 2  # Give Windows time to fully remove the service
}

# Verify Python path exists
if (!(Test-Path $PythonPath)) {
    Write-Host "ERROR: Python executable not found at $PythonPath" -ForegroundColor Red
    Write-Host "Checking for Python installations..."
    $PythonInstalls = Get-ChildItem "C:\Users\User\AppData\Local\Programs\Python" -Directory -ErrorAction SilentlyContinue
    if ($PythonInstalls) {
        Write-Host "Found Python installations: $($PythonInstalls.Name -join ', ')"
        $PossiblePython = Get-ChildItem "C:\Users\User\AppData\Local\Programs\Python" -Recurse -Filter "python.exe" | Select-Object -First 1
        if ($PossiblePython) {
            Write-Host "Using this Python path instead: $($PossiblePython.FullName)" -ForegroundColor Green
            $PythonPath = $PossiblePython.FullName
        }
    }
    else {
        Write-Host "No Python installations found. Please install Python or correct the path." -ForegroundColor Red
        exit 1
    }
}

# Verify Python script exists
if (!(Test-Path $ExecutablePath)) {
    Write-Host "ERROR: Python script not found at $ExecutablePath" -ForegroundColor Red
    exit 1
}

# Install required Python packages
Write-Host "Installing required Python packages..." -ForegroundColor Yellow
foreach ($package in $RequiredPackages) {
    Write-Host "Installing $package..." -ForegroundColor Yellow
    & $PythonPath -m pip install $package
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Failed to install $package. Please install it manually:" -ForegroundColor Red
        Write-Host "$PythonPath -m pip install $package" -ForegroundColor Yellow
        exit 1
    }
    else {
        Write-Host "$package installed successfully." -ForegroundColor Green
    }
}

# Verify packages after installation
Write-Host "Verifying packages..." -ForegroundColor Yellow
foreach ($package in $RequiredPackages) {
    $packageName = $package.Replace('.py', '').Replace('-', '_')
    $checkCmd = "try:
    import $packageName
    print('OK')
except ImportError:
    print('MISSING')"
    
    $tempFile = [System.IO.Path]::GetTempFileName() + ".py"
    $checkCmd | Out-File -FilePath $tempFile -Encoding ascii
    
    $result = & $PythonPath $tempFile
    Remove-Item $tempFile -Force
    
    if ($result -ne "OK") {
        Write-Host "Package $package verification failed. Please install it manually:" -ForegroundColor Red
        Write-Host "$PythonPath -m pip install $package" -ForegroundColor Yellow
        exit 1
    }
    else {
        Write-Host "Package $package verified successfully." -ForegroundColor Green
    }
}

# Create logs directory if it doesn't exist
if (!(Test-Path "$WorkingDirectory\logs")) {
    New-Item -Path "$WorkingDirectory\logs" -ItemType Directory | Out-Null
}

# Create the service using NSSM
Write-Host "Creating service with NSSM..."

# Install the service
& $NssmPath install $ServiceName $PythonPath "`"$ExecutablePath`""

# Configure the service
& $NssmPath set $ServiceName AppDirectory $WorkingDirectory
& $NssmPath set $ServiceName DisplayName "AI News Bot Service"
& $NssmPath set $ServiceName Description "AI News Bot Service - Runs Python script at login"

# Configure logging
& $NssmPath set $ServiceName AppStdout "$WorkingDirectory\logs\service_stdout.log"
& $NssmPath set $ServiceName AppStderr "$WorkingDirectory\logs\service_stderr.log"

# Set restart behavior
& $NssmPath set $ServiceName AppRestartDelay 5000
& $NssmPath set $ServiceName AppExit 0 Restart
& $NssmPath set $ServiceName AppExit 1 Restart

# Configure service to start automatically
& $NssmPath set $ServiceName Start SERVICE_AUTO_START

# Try to start the service
Write-Host "Attempting to start the service..."
try {
    Start-Service -Name $ServiceName -ErrorAction Stop
    Write-Host "Service $ServiceName has been successfully started." -ForegroundColor Green
}
catch {
    Write-Host "Failed to start service. Error: $_" -ForegroundColor Red
    Write-Host "Checking service status..."
    $ServiceStatus = Get-Service -Name $ServiceName
    Write-Host "Service status: $($ServiceStatus.Status)"
    
    Write-Host "Checking Windows Event Log for errors..."
    Get-EventLog -LogName System -Newest 10 -EntryType Error, Warning | 
    Where-Object { $_.Message -like "*$ServiceName*" } | 
    Format-List
    
    Write-Host "Looking for service logs..."
    if (Test-Path "$WorkingDirectory\logs\service_stderr.log") {
        Write-Host "Contents of service_stderr.log:" -ForegroundColor Yellow
        Get-Content "$WorkingDirectory\logs\service_stderr.log" -Tail 20
    }
    
    # Test if we can manually run the command
    Write-Host "Testing if we can manually run the Python script..."
    try {
        $Command = "$PythonPath `"$ExecutablePath`""
        Write-Host "Command: $Command"
        Start-Process -FilePath $PythonPath -ArgumentList "`"$ExecutablePath`"" -WorkingDirectory $WorkingDirectory -NoNewWindow -Wait
        Write-Host "Manual execution completed." -ForegroundColor Green
    }
    catch {
        Write-Host "Manual execution failed: $_" -ForegroundColor Red
    }
}

Write-Host "Service setup complete. Check the logs directory for any issues." -ForegroundColor Green
Write-Host "Service logs are located at $WorkingDirectory\logs\" -ForegroundColor Yellow