Question  
      ↓ (Decomposition)  
  Claims  
      ↓ (Classification)  
  Results  

# for Windows 10

Download JDK and set $JAVA_HOME in environmental variables.

Add the path to `jvm.dll` to Path in environmental variables, too.

Then,  

```cmd
conda install -c conda-forge faiss
conda install pytorch torchvision torchaudio cpuonly -c pytorch
```

Annotation Platform
question, facts, decompositon, evidence (combine articles into choices, both title and contents)
reference: https://allenai.org/data/strategyqa